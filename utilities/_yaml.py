from typing import Dict

def replace_placeholders(yaml_content: str, replacements: Dict) -> str:
    """Replace templated placeholders with the given replacement values.

    This is primarily used for secret replacement and injection. Can be extended
    based on your tailscale operator requirements.

    Parameters
    ----------
    yaml_content: str
    replacements: Dict

    Returns
    -------
    str
    """
    for key, value in replacements.items():
        yaml_content = yaml_content.replace(f'#{key}#', value)
    return yaml_content
