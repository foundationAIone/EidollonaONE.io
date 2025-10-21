/**
 * Basic GLTFLoader for Three.js
 * Simplified version for avatar loading
 */

THREE.GLTFLoader = function ( manager ) {
    this.manager = ( manager !== undefined ) ? manager : THREE.DefaultLoadingManager;
    this.dracoLoader = null;
    this.ktx2Loader = null;
    this.meshoptDecoder = null;
    this.pluginCallbacks = [];
    this.register( function ( parser ) {
        return new GLTFMaterialsClearcoatExtension( parser );
    } );
    this.register( function ( parser ) {
        return new GLTFTextureBasisUExtension( parser );
    } );
    this.register( function ( parser ) {
        return new GLTFTextureWebPExtension( parser );
    } );
    this.register( function ( parser ) {
        return new GLTFMaterialsVolumeExtension( parser );
    } );
    this.register( function ( parser ) {
        return new GLTFMaterialsTransmissionExtension( parser );
    } );
    this.register( function ( parser ) {
        return new GLTFMaterialsIorExtension( parser );
    } );
    this.register( function ( parser ) {
        return new GLTFMaterialsSpecularExtension( parser );
    } );
    this.register( function ( parser ) {
        return new GLTFMaterialsSheenExtension( parser );
    } );
    this.register( function ( parser ) {
        return new GLTFLightsExtension( parser );
    } );
    this.register( function ( parser ) {
        return new GLTFMeshoptCompression( parser );
    } );
};

THREE.GLTFLoader.prototype = Object.assign( Object.create( THREE.Loader.prototype ), {
    constructor: THREE.GLTFLoader,
    
    load: function ( url, onLoad, onProgress, onError ) {
        var scope = this;
        var resourcePath;
        
        if ( this.resourcePath !== '' ) {
            resourcePath = this.resourcePath;
        } else if ( this.path !== '' ) {
            resourcePath = this.path;
        } else {
            resourcePath = THREE.LoaderUtils.extractUrlBase( url );
        }

        // Use FileLoader to load the GLB/GLTF file
        var loader = new THREE.FileLoader( this.manager );
        loader.setPath( this.path );
        loader.setResponseType( 'arraybuffer' );
        loader.setRequestHeader( this.requestHeader );
        loader.setWithCredentials( this.withCredentials );
        
        loader.load( url, function ( data ) {
            try {
                scope.parse( data, resourcePath, function ( gltf ) {
                    onLoad( gltf );
                }, onError );
            } catch ( e ) {
                if ( onError ) {
                    onError( e );
                } else {
                    console.error( e );
                }
                scope.manager.itemError( url );
            }
        }, onProgress, onError );
    },

    parse: function ( data, path, onLoad, onError ) {
        var content;
        var extensions = {};
        var plugins = {};
        
        if ( typeof data === 'string' ) {
            content = data;
        } else {
            var magic = THREE.LoaderUtils.decodeText( new Uint8Array( data, 0, 4 ) );
            if ( magic === 'glTF' ) {
                // Binary GLB format
                var view = new DataView( data );
                var length = view.getUint32( 8, true );
                var chunkLength = view.getUint32( 12, true );
                var chunkType = view.getUint32( 16, true );
                
                if ( chunkType === 0x4E4F534A ) { // JSON chunk
                    var contentArray = new Uint8Array( data, 20, chunkLength );
                    content = THREE.LoaderUtils.decodeText( contentArray );
                }
                
                // Binary buffer chunk (if present)
                if ( 20 + chunkLength < length ) {
                    var binaryChunkLength = view.getUint32( 20 + chunkLength, true );
                    var binaryChunkType = view.getUint32( 20 + chunkLength + 4, true );
                    
                    if ( binaryChunkType === 0x004E4942 ) { // BIN chunk
                        var binaryBuffer = data.slice( 20 + chunkLength + 8, 20 + chunkLength + 8 + binaryChunkLength );
                        extensions.binary = binaryBuffer;
                    }
                }
            } else {
                content = THREE.LoaderUtils.decodeText( new Uint8Array( data ) );
            }
        }
        
        var json = JSON.parse( content );
        
        if ( json.asset === undefined || json.asset.version[ 0 ] < 2 ) {
            if ( onError ) onError( new Error( 'THREE.GLTFLoader: Unsupported asset. glTF versions >=2.0 are supported.' ) );
            return;
        }

        var parser = new GLTFParser( json, {
            path: path || this.resourcePath || '',
            crossOrigin: this.crossOrigin,
            requestHeader: this.requestHeader,
            manager: this.manager,
            ktx2Loader: this.ktx2Loader,
            meshoptDecoder: this.meshoptDecoder
        } );

        parser.fileLoader = new THREE.FileLoader( this.manager );
        parser.fileLoader.setRequestHeader( this.requestHeader );

        for ( var i = 0; i < this.pluginCallbacks.length; i ++ ) {
            var plugin = this.pluginCallbacks[ i ]( parser );
            plugins[ plugin.name ] = plugin;
            extensions[ plugin.name ] = true;
        }

        parser.setExtensions( extensions );
        parser.setPlugins( plugins );
        parser.parse( onLoad, onError );
    },

    register: function ( callback ) {
        if ( this.pluginCallbacks.indexOf( callback ) === - 1 ) {
            this.pluginCallbacks.push( callback );
        }
        return this;
    },

    unregister: function ( callback ) {
        if ( this.pluginCallbacks.indexOf( callback ) !== - 1 ) {
            this.pluginCallbacks.splice( this.pluginCallbacks.indexOf( callback ), 1 );
        }
        return this;
    }
});

// Simplified GLTFParser
function GLTFParser( json, options ) {
    this.json = json || {};
    this.options = options || {};
    this.fileLoader = new THREE.FileLoader();
    this.textureLoader = new THREE.TextureLoader();
}

GLTFParser.prototype = {
    parse: function ( onLoad, onError ) {
        var parser = this;
        var json = this.json;
        
        // Create a simple scene with the first mesh
        var scene = new THREE.Scene();
        
        if ( json.scenes && json.scenes.length > 0 ) {
            var sceneIndex = json.scene !== undefined ? json.scene : 0;
            var sceneDef = json.scenes[ sceneIndex ];
            
            if ( sceneDef.nodes ) {
                for ( var i = 0; i < sceneDef.nodes.length; i++ ) {
                    var nodeIndex = sceneDef.nodes[ i ];
                    this.buildNodeHierarchy( nodeIndex, scene );
                }
            }
        }
        
        // Create animations array (empty for now)
        var animations = [];
        
        onLoad({
            scene: scene,
            scenes: [ scene ],
            animations: animations,
            cameras: [],
            asset: json.asset || {},
            parser: parser,
            userData: {}
        });
    },
    
    buildNodeHierarchy: function ( nodeIndex, parent ) {
        var json = this.json;
        var nodeDef = json.nodes[ nodeIndex ];
        
        if ( !nodeDef ) return null;
        
        var node = new THREE.Object3D();
        
        if ( nodeDef.name ) node.name = nodeDef.name;
        
        // Apply transforms
        if ( nodeDef.matrix ) {
            var matrix = new THREE.Matrix4();
            matrix.fromArray( nodeDef.matrix );
            node.applyMatrix4( matrix );
        } else {
            if ( nodeDef.translation ) {
                node.position.fromArray( nodeDef.translation );
            }
            if ( nodeDef.rotation ) {
                node.quaternion.fromArray( nodeDef.rotation );
            }
            if ( nodeDef.scale ) {
                node.scale.fromArray( nodeDef.scale );
            }
        }
        
        // Add mesh if present
        if ( nodeDef.mesh !== undefined ) {
            var mesh = this.buildMesh( nodeDef.mesh );
            if ( mesh ) {
                node.add( mesh );
            }
        }
        
        parent.add( node );
        
        // Process child nodes
        if ( nodeDef.children ) {
            for ( var i = 0; i < nodeDef.children.length; i++ ) {
                this.buildNodeHierarchy( nodeDef.children[ i ], node );
            }
        }
        
        return node;
    },
    
    buildMesh: function ( meshIndex ) {
        var json = this.json;
        var meshDef = json.meshes[ meshIndex ];
        
        if ( !meshDef || !meshDef.primitives ) return null;
        
        // For simplicity, just use the first primitive
        var primitive = meshDef.primitives[ 0 ];
        
        // Create basic geometry and material
        var geometry = new THREE.BufferGeometry();
        var material = new THREE.MeshBasicMaterial( { color: 0x888888 } );
        
        // Create a simple mesh
        var mesh = new THREE.Mesh( geometry, material );
        if ( meshDef.name ) mesh.name = meshDef.name;
        
        return mesh;
    },
    
    setExtensions: function ( extensions ) {
        this.extensions = extensions;
    },
    
    setPlugins: function ( plugins ) {
        this.plugins = plugins;
    }
};

// Empty extension classes for compatibility
function GLTFMaterialsClearcoatExtension() { this.name = 'KHR_materials_clearcoat'; }
function GLTFTextureBasisUExtension() { this.name = 'KHR_texture_basisu'; }
function GLTFTextureWebPExtension() { this.name = 'EXT_texture_webp'; }
function GLTFMaterialsVolumeExtension() { this.name = 'KHR_materials_volume'; }
function GLTFMaterialsTransmissionExtension() { this.name = 'KHR_materials_transmission'; }
function GLTFMaterialsIorExtension() { this.name = 'KHR_materials_ior'; }
function GLTFMaterialsSpecularExtension() { this.name = 'KHR_materials_specular'; }
function GLTFMaterialsSheenExtension() { this.name = 'KHR_materials_sheen'; }
function GLTFLightsExtension() { this.name = 'KHR_lights_punctual'; }
function GLTFMeshoptCompression() { this.name = 'EXT_meshopt_compression'; }