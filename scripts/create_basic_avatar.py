#!/usr/bin/env python3
"""Create a basic GLB avatar placeholder."""

import json
import struct
from pathlib import Path


def create_basic_glb():
    """Create a minimal GLB file with a simple cube."""
    
    # Simple cube mesh data (positions, normals, indices)
    positions = [
        -1.0, -1.0,  1.0,  # 0
         1.0, -1.0,  1.0,  # 1
         1.0,  1.0,  1.0,  # 2
        -1.0,  1.0,  1.0,  # 3
        -1.0, -1.0, -1.0,  # 4
         1.0, -1.0, -1.0,  # 5
         1.0,  1.0, -1.0,  # 6
        -1.0,  1.0, -1.0,  # 7
    ]
    
    indices = [
        0, 1, 2,  0, 2, 3,  # front
        4, 7, 6,  4, 6, 5,  # back
        0, 4, 5,  0, 5, 1,  # bottom
        2, 6, 7,  2, 7, 3,  # top
        0, 3, 7,  0, 7, 4,  # left
        1, 5, 6,  1, 6, 2,  # right
    ]
    
    # Pack binary data
    positions_bytes = struct.pack(f'{len(positions)}f', *positions)
    indices_bytes = struct.pack(f'{len(indices)}H', *indices)
    
    # Minimal glTF JSON
    gltf_json = {
        "asset": {"version": "2.0", "generator": "EidollonaONE"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{
            "primitives": [{
                "attributes": {"POSITION": 0},
                "indices": 1
            }]
        }],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,  # FLOAT
                "count": 8,
                "type": "VEC3",
                "min": [-1.0, -1.0, -1.0],
                "max": [1.0, 1.0, 1.0]
            },
            {
                "bufferView": 1,
                "componentType": 5123,  # UNSIGNED_SHORT
                "count": 36,
                "type": "SCALAR"
            }
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(positions_bytes)},
            {"buffer": 0, "byteOffset": len(positions_bytes), "byteLength": len(indices_bytes)}
        ],
        "buffers": [{"byteLength": len(positions_bytes) + len(indices_bytes)}]
    }
    
    # Create GLB
    json_str = json.dumps(gltf_json, separators=(',', ':'))
    json_bytes = json_str.encode('utf-8')
    
    # Pad to 4-byte boundary
    json_padding = (4 - len(json_bytes) % 4) % 4
    json_bytes += b' ' * json_padding
    
    binary_data = positions_bytes + indices_bytes
    binary_padding = (4 - len(binary_data) % 4) % 4
    binary_data += b'\x00' * binary_padding
    
    # GLB header
    magic = b'glTF'
    version = struct.pack('<I', 2)
    total_length = 12 + 8 + len(json_bytes) + 8 + len(binary_data)
    length = struct.pack('<I', total_length)
    
    # JSON chunk
    json_chunk_length = struct.pack('<I', len(json_bytes))
    json_chunk_type = b'JSON'
    
    # BIN chunk
    bin_chunk_length = struct.pack('<I', len(binary_data))
    bin_chunk_type = b'BIN\x00'
    
    # Assemble GLB
    glb_data = (magic + version + length + 
                json_chunk_length + json_chunk_type + json_bytes +
                bin_chunk_length + bin_chunk_type + binary_data)
    
    return glb_data


def main():
    """Create basic avatar models."""
    repo_root = Path(__file__).parent.parent
    models_dir = repo_root / "web_interface" / "static" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    print("🔧 Creating basic GLB avatar...")
    
    try:
        glb_data = create_basic_glb()
        
        # Create the main files
        files = ["eidollona.glb", "steward_prime.glb", "avatar.glb"]
        for filename in files:
            filepath = models_dir / filename
            with open(filepath, 'wb') as f:
                f.write(glb_data)
            print(f"✅ Created: {filepath} ({len(glb_data)} bytes)")
        
        print("\n🎯 Basic avatar models ready!")
        print("🌐 Refresh throne room to see avatar placeholder")
        print("💡 Replace with real GLB files for better avatars")
        
    except Exception as e:
        print(f"❌ Creation failed: {e}")


if __name__ == "__main__":
    main()