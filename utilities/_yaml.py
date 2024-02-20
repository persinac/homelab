from typing import Dict
import pulumi

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
        # if isinstance(value, pulumi.Output):
        #     yaml_content = yaml_content.replace(
        #         f'#{key}#',
        #         value.apply(lambda token: print(token))
        #     )
        # else:
        yaml_content = yaml_content.replace(f'#{key}#', value)
    return yaml_content
