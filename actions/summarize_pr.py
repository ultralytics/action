# Ultralytics Actions 🚀, AGPL-3.0 license https://ultralytics.com/license

import time

import requests

from .utils import (
    GITHUB_API_URL,
    GITHUB_HEADERS,
    GITHUB_REPOSITORY,
    PR,
    get_completion,
    get_github_username,
    get_pr_diff,
)

# Constants
SUMMARY_START = (
    "## 🛠️ PR Summary\n\n<sub>Made with ❤️ by [Ultralytics Actions](https://github.com/ultralytics/actions)<sub>\n\n"
)


def generate_merge_message(pr_author, contributors, pr_summary=None):
    """Generates a thank-you message for merged PR contributors."""
    contributors_str = ", ".join(f"@{c}" for c in contributors if c != pr_author)
    mention_str = f"@{pr_author}"
    if contributors_str:
        mention_str += f" and {contributors_str}"

    messages = [
        {
            "role": "system",
            "content": "You are an Ultralytics AI assistant. Generate meaningful, inspiring messages to GitHub users.",
        },
        {
            "role": "user",
            "content": f"Write a friendly thank you for a merged PR by these GitHub contributors: {mention_str}. "
            f"Context from PR:\n{pr_summary}\n\n"
            f"Start with the exciting message that this PR is now merged, and weave in an inspiring quote "
            f"from a famous figure in science, philosophy or stoicism. "
            f"Keep the message concise yet relevant to the specific contributions in this PR. "
            f"We want the contributors to feel their effort is appreciated and will make a difference in the world.",
        },
    ]
    return get_completion(messages)


def post_merge_message(pr_number, pr_author, contributors, summary):
    """Posts thank you message on PR after merge."""
    message = generate_merge_message(pr_author, contributors, summary)
    comment_url = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/issues/{pr_number}/comments"
    response = requests.post(comment_url, json={"body": message}, headers=GITHUB_HEADERS)
    return response.status_code == 201


def generate_issue_comment(pr_url, pr_summary):
    """Generates a personalized issue comment using based on the PR context."""
    messages = [
        {
            "role": "system",
            "content": "You are an Ultralytics AI assistant. Generate friendly GitHub issue comments. No @ mentions or direct addressing.",
        },
        {
            "role": "user",
            "content": f"Write a GitHub issue comment announcing a potential fix has been merged in linked PR {pr_url}\n\n"
            f"Context from PR:\n{pr_summary}\n\n"
            f"Include:\n"
            f"1. An explanation of key changes from the PR that may resolve this issue\n"
            f"2. Options for testing if PR changes have resolved this issue:\n"
            f"   - pip install git+https://github.com/ultralytics/ultralytics.git@main # test latest changes\n"
            f"   - or await next official PyPI release\n"
            f"3. Request feedback on whether the PR changes resolve the issue\n"
            f"4. Thank 🙏 for reporting the issue and welcome any further feedback if the issue persists\n\n",
        },
    ]
    return get_completion(messages)


def generate_pr_summary(repo_name, diff_text):
    """Generates a concise, professional summary of a PR using OpenAI's API for Ultralytics repositories."""
    if not diff_text:
        diff_text = "**ERROR: DIFF IS EMPTY, THERE ARE ZERO CODE CHANGES IN THIS PR."
    ratio = 3.3  # about 3.3 characters per token
    limit = round(128000 * ratio * 0.5)  # use up to 50% of the 128k context window for prompt
    messages = [
        {
            "role": "system",
            "content": "You are an Ultralytics AI assistant skilled in software development and technical communication. Your task is to summarize GitHub PRs from Ultralytics in a way that is accurate, concise, and understandable to both expert developers and non-expert users. Focus on highlighting the key changes and their impact in simple, concise terms.",
        },
        {
            "role": "user",
            "content": f"Summarize this '{repo_name}' PR, focusing on major changes, their purpose, and potential impact. Keep the summary clear and concise, suitable for a broad audience. Add emojis to enliven the summary. Reply directly with a summary along these example guidelines, though feel free to adjust as appropriate:\n\n"
            f"### 🌟 Summary (single-line synopsis)\n"
            f"### 📊 Key Changes (bullet points highlighting any major changes)\n"
            f"### 🎯 Purpose & Impact (bullet points explaining any benefits and potential impact to users)\n"
            f"\n\nHere's the PR diff:\n\n{diff_text[:limit]}",
        },
    ]
    reply = get_completion(messages)
    if len(diff_text) > limit:
        reply = "**WARNING ⚠️** this PR is very large, summary may not cover all changes.\n\n" + reply
    return SUMMARY_START + reply


def update_pr_description(repo_name, pr_number, new_summary, max_retries=2):
    """Updates PR description with new summary, retrying if description is None."""
    pr_url = f"{GITHUB_API_URL}/repos/{repo_name}/pulls/{pr_number}"
    description = ""
    for i in range(max_retries + 1):
        description = requests.get(pr_url, headers=GITHUB_HEADERS).json().get("body") or ""
        if description:
            break
        if i < max_retries:
            print("No current PR description found, retrying...")
            time.sleep(1)

    # Check if existing summary is present and update accordingly
    start = "## 🛠️ PR Summary"
    if start in description:
        print("Existing PR Summary found, replacing.")
        updated_description = description.split(start)[0] + new_summary
    else:
        print("PR Summary not found, appending.")
        updated_description = description + "\n\n" + new_summary

    # Update the PR description
    update_response = requests.patch(pr_url, json={"body": updated_description}, headers=GITHUB_HEADERS)
    return update_response.status_code


def label_fixed_issues(pr_number, pr_summary):
    """Labels issues closed by this PR when merged, notifies users, and returns PR contributors."""
    query = """
query($owner: String!, $repo: String!, $pr_number: Int!) {
    repository(owner: $owner, name: $repo) {
        pullRequest(number: $pr_number) {
            closingIssuesReferences(first: 50) {
                nodes {
                    number
                }
            }
            url
            body
            author { login, __typename }
            reviews(first: 50) {
                nodes { author { login, __typename } }
            }
            comments(first: 50) {
                nodes { author { login, __typename } }
            }
        }
    }
}
"""

    owner, repo = GITHUB_REPOSITORY.split("/")
    variables = {"owner": owner, "repo": repo, "pr_number": pr_number}
    graphql_url = "https://api.github.com/graphql"
    response = requests.post(graphql_url, json={"query": query, "variables": variables}, headers=GITHUB_HEADERS)
    if response.status_code != 200:
        print(f"Failed to fetch linked issues. Status code: {response.status_code}")
        return [], None

    try:
        data = response.json()["data"]["repository"]["pullRequest"]
        comments = data["reviews"]["nodes"] | data["comments"]["nodes"]
        author = data["author"]["login"]

        # Get unique contributors from reviews and comments
        contributors = {x["author"]["login"] for x in comments if x["author"]["__typename"] != "Bot"}
        contributors.discard(author)  # Remove author from contributors list

        # Generate personalized comment
        comment = generate_issue_comment(pr_url=data["url"], pr_summary=pr_summary)

        # Update linked issues
        for issue in data["closingIssuesReferences"]["nodes"]:
            issue_number = issue["number"]
            # Add fixed label
            label_url = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/issues/{issue_number}/labels"
            label_response = requests.post(label_url, json={"labels": ["fixed"]}, headers=GITHUB_HEADERS)

            # Add comment
            comment_url = f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/issues/{issue_number}/comments"
            comment_response = requests.post(comment_url, json={"body": comment}, headers=GITHUB_HEADERS)

            if label_response.status_code == 200 and comment_response.status_code == 201:
                print(f"Added 'fixed' label and comment to issue #{issue_number}")
            else:
                print(
                    f"Failed to update issue #{issue_number}. Label status: {label_response.status_code}, "
                    f"Comment status: {comment_response.status_code}"
                )

        return contributors, author
    except KeyError as e:
        print(f"Error parsing GraphQL response: {e}")
        return [], None


def remove_todos_on_merge(pr_number):
    """Removes specified labels from PR."""
    for label in ["TODO"]:  # Can be extended with more labels in the future
        requests.delete(
            f"{GITHUB_API_URL}/repos/{GITHUB_REPOSITORY}/issues/{pr_number}/labels/{label}", headers=GITHUB_HEADERS
        )


def main():
    """Summarize a pull request and update its description with a summary."""
    pr_number = PR["number"]

    print(f"Retrieving diff for PR {pr_number}")
    diff = get_pr_diff(pr_number)

    # Generate PR summary
    print("Generating PR summary...")
    summary = generate_pr_summary(GITHUB_REPOSITORY, diff)

    # Update PR description
    print("Updating PR description...")
    status_code = update_pr_description(GITHUB_REPOSITORY, pr_number, summary)
    if status_code == 200:
        print("PR description updated successfully.")
    else:
        print(f"Failed to update PR description. Status code: {status_code}")

    # Update linked issues and post thank you message if merged
    if PR.get("merged"):
        print("PR is merged, labeling fixed issues...")
        contributors, author = label_fixed_issues(pr_number, summary)
        print("Removing TODO label from PR...")
        remove_todos_on_merge(pr_number)
        username = get_github_username()  # get GITHUB_TOKEN username
        if author and author != username:
            print("Posting PR author thank you message...")
            contributors.discard(username)
            post_merge_message(pr_number, author, contributors, summary)


if __name__ == "__main__":
    main()
