# Ethics

## Consent records

**No real person appears or is voiced.** Abebe, Kassa and their younger
selves are fictional. Their faces come from text descriptions, and their
voices are stock Gemini voices (`Algenib`, `am-et-assistant-1`). Every
character has `real_person: false` in `storyboard.json`. The author asked
for no imitation of real people or celebrities. The image prompts name no
person, and no reference photo of a real person was used.

If a real person is ever added, add one heading per real person whose face, likeness or voice appears, before
anything of them is generated. The heading text is that character's
`consent_ref` in `storyboard.json`, and `make validate` checks it exists.
Under each heading record what was consented to, the date, how it was
recorded, and where the recording is kept outside this repository.

## Family agreement on data sent to providers

The dialogue is a fictional script written by the author, not private
family material. Sending it to the free tier of the Gemini API, which may use
inputs to improve Google's products, exposes no private family details. The
author approved this route (design decision D4).

## Data sent to each provider

| Provider | What is sent |
| --- | --- |
| Gemini API (free tier) | Dialogue text, one line per call; voice name; delivery style |
| Cloudflare Workers AI | Image prompts and reference images |
| Kaggle | Keyframes and motion prompts (private dataset and kernels) |

## Licences

| Model or output | Licence |
| --- | --- |
| Wan 2.2 TI2V-5B | Apache 2.0 (used only if a shot is animated) |
| FLUX.2 klein 4B | Apache 2.0 |
| ACE-Step 1.5 turbo | MIT (code and model card). The model card says outputs may be used commercially. |
| Gemini API outputs | Gemini API terms of use |
| Placeholder track | Generated locally from FFmpeg signal sources |

## Labelling plan

*   A 3 s end card in the film says it was made with AI and names the models.
*   The platform's AI-content label is switched on when posting.
*   Watermarks and provenance metadata from the models are left intact.

## Sensitive subject

Dementia is shown with dignity: the person with the illness is never the
joke, and the closing cards point to recognising signs and seeking help.
They do not make a medical claim.

The closing card's term "የአእምሮ መታወክ (ዲሜንሺያ)" should be checked by a
fluent speaker before release. It can read as "mental disorder", which may
stigmatise. "የመርሳት በሽታ" is a possible gentler alternative.
