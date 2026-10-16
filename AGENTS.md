# Agent operating rules

- Work in this repo. Do not copy the local-audio caches, credentials, outputs, environments or entire upstream repositories into it.
- On this PC, write project files, logs, temporary files and caches on D:. Existing system executables may be reused read-only. Colab files live under `/content`.
- Never commit tokens, passwords, signed URLs, notebook outputs, generated audio or model weights. The notebook bundle must contain only the explicit source allowlist in `tools/build_notebook.py`.
- The user authorized a public GitHub repository. Keep credentials, notebook outputs, models and generated audio out of all commits. Publishing source does not authorize removing the domain's Cloudflare Access policy.
- GPU inference is mandatory. CPU/system-memory weight offload and disk-backed loading are allowed; CPU generation is not. Do not pass `--cpu`, `--cpu-vae` or `--lowvram`, which can select CPU text inference.
- Use only one owned GPU backend at a time; never terminate the user's editors or unrelated processes. `studio.worker` holds an OS-released process lock. On this PC set `STUDIO_GPU_LOCK` to the existing local-audio `jobs/gpu-model.lock` if reusing its GPU.
- Preserve originals; editing exports are stereo 48 kHz PCM24. Technical checks are not a listening review. Maximum duration is not a guaranteed exact length.
- Free Colab: generate directly through the notebook form. The external UI/tunnel launcher is optional for paid Colab with positive compute units or a GPU host the user controls. No keep-alive or limit-bypass behavior.
- Ask for the domain/login name with input() and password/token with getpass() at runtime. Do not store them in notebook form parameters or source. Clear the temporary environment dictionary when the launcher exits. Do not copy the user's chat token into source. If it has been shared, let the user rotate it. Pass it only to cloudflared's environment, not command-line arguments or ML workers.
- Rebuild `MiniMax_Music_Studio.ipynb` after source edits. Clear notebook outputs; run the focused tests. Do not run real-GPU operational scripts as broad test discovery.
- `tools/test_generation.py` performs a real authenticated web-UI generation on the configured PC. It expects ignored `.runtime/test-auth.json`. Run it only deliberately while the other studio's model is released.
- Record exact verification limits in VALIDATION.md. Windows generation does not prove a Colab/T4 run or a live Cloudflare connection.
