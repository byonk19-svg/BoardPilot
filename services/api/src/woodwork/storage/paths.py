from pathlib import Path
from woodwork.storage import StoreError


def contained_file(root:Path,relative:str):
    path=root/relative
    if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
        raise StoreError(409,'ARTIFACT_UNAVAILABLE','This saved artifact is missing or outside the project store. Regenerate the revision.')
    for parent in path.parents:
        if parent==root:break
        if parent.is_symlink() or (hasattr(parent,'is_junction') and parent.is_junction()):
            raise StoreError(409,'ARTIFACT_UNAVAILABLE','An artifact directory is a filesystem link. Regenerate the revision.')
    return path
