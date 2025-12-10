"""
Asset copier for open-dateaubase documentation.
This script copies generated HTML plot files to locations that MkDocs will serve properly.
It registers the files with mkdocs_gen_files so they're included in the build.
"""
from pathlib import Path
import mkdocs_gen_files

def copy_generated_assets():
    """Copy generated HTML assets to be served by MkDocs."""
    
    # Source directory with generated assets (relative to project root/docs)
    # The hook runs with CWD as project root
    assets_dir = Path('docs/assets')
    
    if not assets_dir.exists():
        print("No assets directory found")
        return
    
    # Files to copy - specifically the generated ERD files
    generated_files = [
        'erd_interactive.html'
    ]
    
    print(f"Checking for assets in {assets_dir.absolute()}")
    
    for filename in generated_files:
        source_path = assets_dir / filename
        if source_path.exists():
            # Target path in the built site (assets/filename)
            target_path = f"assets/{filename}"
            
            print(f"Copying {filename} -> {target_path}")
            
            # Read content and write to mkdocs_gen_files
            # This ensures MkDocs knows about these files and puts them in the site
            try:
                content = source_path.read_text(encoding='utf-8')
                with mkdocs_gen_files.open(target_path, "w") as f:
                    f.write(content)
            except Exception as e:
                print(f"Error copying {filename}: {e}")
        else:
            print(f"Warning: Expected asset {filename} not found in {assets_dir}")

copy_generated_assets()
