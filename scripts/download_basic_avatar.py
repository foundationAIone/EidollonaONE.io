#!/usr/bin/env python3
"""Download a basic avatar model for testing purposes."""

import urllib.request
from pathlib import Path


def download_basic_avatar():
    """Download a basic GLB avatar model for testing."""
    repo_root = Path(__file__).parent.parent
    models_dir = repo_root / "web_interface" / "static" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    # Simple cube avatar for testing (from Three.js examples)
    test_glb_url = "https://threejs.org/examples/models/gltf/DamagedHelmet/glTF-Binary/DamagedHelmet.glb"
    target_file = models_dir / "eidollona.glb"
    
    print("🔽 Downloading basic avatar model...")
    print(f"📍 URL: {test_glb_url}")
    print(f"📁 Target: {target_file}")
    
    try:
        urllib.request.urlretrieve(test_glb_url, str(target_file))
        print(f"✅ Downloaded: {target_file}")
        print(f"📏 Size: {target_file.stat().st_size / 1024:.1f} KB")
        
        # Create additional expected files as symlinks/copies
        copies = ["steward_prime.glb", "avatar.glb"]
        for copy_name in copies:
            copy_path = models_dir / copy_name
            if not copy_path.exists():
                # Copy the file
                import shutil
                shutil.copy2(target_file, copy_path)
                print(f"📋 Copied to: {copy_path}")
        
        print("\n🎯 Avatar models ready!")
        print("🌐 Refresh throne room to see avatar")
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        print("💡 Manual: Download any GLB file to web_interface/static/models/eidollona.glb")


if __name__ == "__main__":
    download_basic_avatar()