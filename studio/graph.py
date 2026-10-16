"""Native Comfy graph using the official pinned MiniMax conversions."""
def build(request):
    seed = request['seed']
    return {
        '1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': 'minimax_music3_dit_int8_convrot.safetensors', 'weight_dtype': 'default'}},
        '2': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': 'minimax_music3_text_encoder_pruned_int8_convrot.safetensors', 'type': 'minimax', 'device': 'default'}},
        '3': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'minimax_music3_dav.safetensors'}},
        '4': {'class_type': 'MiniMaxMusic3TextEncode', 'inputs': {'clip': ['2', 0], 'caption': request['caption'], 'lyrics': request['lyrics'], 'seed': seed, 'max_duration': request['seconds'], 'cfg_scale': request['guidance'], 'top_k': request['top_k']}},
        '5': {'class_type': 'ConditioningZeroOut', 'inputs': {'conditioning': ['4', 0]}},
        '6': {'class_type': 'EmptyMiniMaxMusic3LatentAudio', 'inputs': {'seconds': ['4', 1], 'batch_size': 1}},
        '7': {'class_type': 'KSampler', 'inputs': {'model': ['1', 0], 'positive': ['4', 0], 'negative': ['5', 0], 'latent_image': ['6', 0], 'seed': seed, 'steps': request['steps'], 'cfg': request['guidance'], 'sampler_name': 'euler', 'scheduler': 'simple', 'denoise': 1}},
        '8': {'class_type': 'VAEDecodeAudioTiled', 'inputs': {'samples': ['7', 0], 'vae': ['3', 0], 'tile_size': 1536, 'overlap': 64}},
        '9': {'class_type': 'SaveAudio', 'inputs': {'audio': ['8', 0], 'filename_prefix': 'worker/music'}},
    }
