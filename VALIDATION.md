# Validation

Date: 2026-10-16. Real CUDA generation passed both on this Windows PC and on a free Colab T4 runtime. Focused source/notebook, audio-tool, login and file-boundary checks passed. A live Cloudflare deployment has not been performed.

## Provenance

The existing Windows installation has already generated MiniMax audio on an RTX 4050 Laptop 6 GB using the pinned official Comfy conversion. This new repo reuses that graph design, with its own app, process lifecycle, prompts, notebook packaging and optional tunnel launcher. Prior installation success does not by itself validate these new components.

The official Hugging Face Space at revision `929e40ed4e425518693ec955ced52aba5ea6c425` was inspected as a design and prompting reference. It uses a full-precision Diffusers pipeline, extra prompt-assistance services and custom streaming/compilation. Those services, credentials, assets and source code were not copied into this repo. This app uses native Comfy nodes and a deterministic brief builder.

## Completed checks

- Six focused tests passed: instrumental conditioning ignores lyric words; invalid/NaN requests fail before GPU work; creative controls reach the native graph; the editing export protects peaks without changing its source or overwriting a result; loops preserve source/length/format; the notebook parses, contains no saved outputs, and embeds exactly the current selected source files.
- Authentication/file-boundary checks passed on the real app: anonymous configuration/download access and wrong passwords were rejected; an authenticated output download succeeded; a private runtime file was denied (`validation/auth-check.json`). No GPU inference was performed for these checks.
- The guided UI was rendered and visually inspected in Chrome. Advanced controls start collapsed, example help text is visible, instrumental mode defaults on, and file downloads are read-only. Screenshots are kept in the ignored local runtime folder.
- A real call through the new password-protected Gradio action generated **4.992 seconds** from a five-second maximum, seed 67891, in **152.26 seconds** including startup. The RTX 4050 6 GB used the existing isolated CUDA 13 backend and verified model files. The original local studio had an idle MiniMax worker loaded; the cross-studio GPU lock correctly refused a second model until that idle worker was released. No editing app was stopped.
- The initial direct resample produced one full-scale sample. The final export function was exercised on the preserved generated FLAC, using a float intermediate and **-0.18968 dB** gain protection. The resulting stereo 48 kHz PCM24 WAV passed finite/non-silent, complete decoding and zero full-scale-sample checks, peak approximately 0.98. Synthetic over-range audio and non-overwrite/source-preservation tests also passed. A second GPU generation was unnecessary for this isolated export change. Evidence: `validation/windows-smoke.json`.
- The existing Cloudflare dashboard route was read: `colab.chocojayy.me → http://localhost:8188`, tunnel down with zero replicas. An existing Cloudflare Access sign-in page is present. No route or access policy was changed.
- The public Colab link opened without GitHub private-repository authorization. A free **T4** runtime with **12.67 GB system RAM** was allocated. Notebook step 1 completed in about five minutes and displayed its final “Ready” message. This step asserts actual CUDA operation, installs the isolated backend, downloads/checks the pinned model files and runs the backend preflight before returning successfully. The first ten-second generation was submitted with seed 12345 through the notebook form.
- The saved Colab job was inspected through a plain-text notebook cell. It reports **succeeded**, **9.996208 seconds**, seed **12345**, 30 steps, guidance 1.7, top-k 50, and **115.17 seconds** from submission through export/QA (backend startup and initial setup excluded). The runtime reports **PyTorch 2.11.0+cu130 / CUDA 13.0 / Tesla T4**. Logs show native quantized operations, completed autoregressive/diffusion sampling, and disk-backed dynamic loading. The Premiere file is stereo 48 kHz PCM24, finite, non-silent, fully decodable, zero full-scale samples, peak approximately 0.98; export gain was -0.12617 dB. Evidence copied from the actual visible saved-job record: `validation/colab-generation.json`.
- Colab's rich output display reported that JavaScript could not load, citing expired Google login or blocked third-party cookies. After a normal refresh, a reCAPTCHA service connectivity warning also appeared. The plain-text inspection nevertheless completed and established successful generation from the saved job; no challenge was bypassed or browser protection disabled. Browser audio playback and downloading were not verified. No browser download was triggered onto the PC's C: drive.

## Remaining checks

- Browser playback/download and human audition after resolving any Google output-display/session issue. The Linux worker enables disk-backed loading and disables node-result caching to reduce system-RAM pressure; the T4 result establishes this ten-second case, not every free runtime or longer 30/60/90-second jobs.
- Live Cloudflare end-to-end testing on an eligible paid runtime or own GPU host with secrets configured. The free account uses the in-notebook generation form. No tunnel was started from free Colab.
- Colab notebook file upload through the browser extension was blocked because that extension does not have file-URL access. That browser setting was not changed.

The repo was initially private as requested, then the user explicitly changed the requirement to public to avoid granting Colab access to private GitHub repositories. Notebook step 4 now asks for its connection details at runtime using input()/getpass(); no GitHub authorization or Colab Secrets setup is required. No tunnel credential was copied from chat into any file or commit.

No human listening quality, music-theory adherence, loop continuity, or Premiere GUI import should be claimed without a separate review.
