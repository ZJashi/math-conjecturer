def format_proposals(proposals: list) -> str:
    parts = []
    for i, p in enumerate(proposals, 1):
        parts.append(
            f"Proposal {i}: {p.get('title', 'Untitled')}\n"
            f"Problem Statement: {p.get('problem_statement', '')}"
        )
    return "\n\n".join(parts)