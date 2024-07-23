# Ultralytics YOLO 🚀, AGPL-3.0 License https://ultralytics.com/license

import json
import os
import time
from typing import Dict, List, Tuple

import requests
from openai import AzureOpenAI, OpenAI

# Environment variables
REPO_NAME = os.getenv("GITHUB_REPOSITORY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_EVENT_NAME = os.getenv("GITHUB_EVENT_NAME")
GITHUB_EVENT_PATH = os.getenv("GITHUB_EVENT_PATH")
GITHUB_API_URL = "https://api.github.com"
GITHUB_HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

# OpenAI settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_AZURE_API_KEY = os.getenv("OPENAI_AZURE_API_KEY")
OPENAI_AZURE_ENDPOINT = os.getenv("OPENAI_AZURE_ENDPOINT")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-2024-05-13")


def openai_client():
    """Returns OpenAI client instance."""
    if OPENAI_AZURE_API_KEY and OPENAI_AZURE_ENDPOINT:
        return AzureOpenAI(
            api_key=OPENAI_AZURE_API_KEY,
            api_version=os.getenv("OPENAI_AZURE_API_VERSION", "2024-05-01-preview"),
            azure_endpoint=OPENAI_AZURE_ENDPOINT,
        )
    return OpenAI(api_key=OPENAI_API_KEY)


def get_github_data(endpoint: str) -> dict:
    """Generic function to fetch data from GitHub API."""
    response = requests.get(f"{GITHUB_API_URL}/repos/{REPO_NAME}/{endpoint}", headers=GITHUB_HEADERS)
    response.raise_for_status()
    return response.json()


def get_event_content() -> Tuple[int, str, str]:
    """Extracts the number, title, and body from the issue or pull request."""
    with open(GITHUB_EVENT_PATH, "r") as f:
        event_data = json.load(f)

    if GITHUB_EVENT_NAME == "issues":
        item = event_data["issue"]
        return item["number"], item["title"], item.get("body", "")
    elif GITHUB_EVENT_NAME in ["pull_request", "pull_request_target"]:
        pr_number = event_data["pull_request"]["number"]

        # Check if this is a newly opened PR
        if event_data["action"] == "opened":
            print("New PR detected. Waiting for 60 seconds before fetching PR data...")
            time.sleep(60)

        # Fetch the latest PR data
        latest_pr_data = get_github_data(f"pulls/{pr_number}")
        return pr_number, latest_pr_data["title"], latest_pr_data.get("body", "")
    else:
        raise ValueError(f"Unsupported event type: {GITHUB_EVENT_NAME}")


def get_relevant_labels(title: str, body: str, available_labels: Dict[str, str]) -> List[str]:
    """Uses OpenAI to determine the most relevant labels."""
    labels = "\n".join(f"- {name}: {description}" for name, description in available_labels.items())

    prompt = f"""Select the top 1-3 most relevant labels for the following GitHub issue or pull request.

INSTRUCTIONS:
1. Review the issue/PR title and description.
2. Consider the available labels and their descriptions.
3. Choose 1-3 labels that best match the issue/PR content.
4. Respond ONLY with the chosen label names (no descriptions), separated by commas.
5. If no labels are relevant, respond with 'None'.

AVAILABLE LABELS:
{labels}

ISSUE/PR TITLE:
{title}

ISSUE/PR DESCRIPTION:
{body[:128000]}

YOUR RESPONSE (label names only):
"""
    print(prompt)

    response = openai_client().chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that labels GitHub issues and pull requests."},
            {"role": "user", "content": prompt},
        ],
    )

    suggested_labels = response.choices[0].message.content.strip()
    if "none" in suggested_labels.lower():
        return []

    available_labels_lower = {name.lower(): name for name in available_labels}
    return [
        available_labels_lower[label.lower().strip()]
        for label in suggested_labels.split(",")
        if label.lower().strip() in available_labels_lower
    ]


def apply_labels(number: int, labels: List[str]):
    """Applies the given labels to the issue or pull request."""
    url = f"{GITHUB_API_URL}/repos/{REPO_NAME}/issues/{number}/labels"
    response = requests.post(url, json={"labels": labels}, headers=GITHUB_HEADERS | {"Author": "UltralyticsAssistant"})
    if response.status_code == 200:
        print(f"Successfully applied labels: {', '.join(labels)}")
    else:
        print(f"Failed to apply labels. Status code: {response.status_code}")


def main():
    """Runs autolabel action."""
    number, title, body = get_event_content()
    available_labels = {label["name"]: label.get("description", "") for label in get_github_data("labels")}
    relevant_labels = get_relevant_labels(title, body, available_labels)
    if relevant_labels:
        apply_labels(number, relevant_labels)
    else:
        print("No relevant labels found or applied.")


if __name__ == "__main__":
    main()
