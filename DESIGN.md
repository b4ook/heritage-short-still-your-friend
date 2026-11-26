# Design

## Audience and intent

*   **Film:** አሁንም ጓደኛህ ነኝ (Still Your Friend). Abebe and Kassa are two
    lifelong friends, both fictional and both in their seventies. Kassa has
    dementia and is losing his memories, including his memory of Abebe. Abebe
    keeps taking him to football matches.
*   **Who watches:**
    *   Ethiopian families, both young adults and older generations.
    *   Families caring for someone with dementia.
    *   Caregivers and health workers.
    *   General audiences of dementia-awareness campaigns.

    The film must make sense to someone who knows nothing about dementia.
*   **Where they watch:** mostly on phones, in a vertical feed (9:16). The
    16:9 cut is for sharing and screenings.
*   **Language:** spoken in Amharic, with English subtitles. The closing
    messages appear on screen in Amharic.
*   **What they should feel at the end:** that friendship and dignity outlast
    memory. They should also take away one plain message: dementia is not
    just old age, so learn the signs, seek help early, and stay with the
    person.
*   **Creative rule:** this is not a medical advertisement. It opens as a warm
    story about two friends and football, and the illness is revealed through
    the friendship, not through a lecture. The awareness message comes only
    on the closing cards.
*   **How might we:** help Ethiopian families see dementia as something to
    recognise and stand beside, not hide, through a story they would forward
    to their own family?

## Shots

Each shot's reason is its `purpose` field in `storyboard.json`. The arc is:

1.  The past (s01).
2.  The first sign, on the phone (s02–s04).
3.  The walk (s05).
4.  The stadium and a flicker of memory (s06–s07).
5.  The goal, joy that survives (s08).
6.  Abebe's tears and promise (s09–s10).
7.  The photo and "I still am" (s11–s12).
8.  The closing messages.

## User test 1: radio cut

*   **Date:**
*   **Who (at least 3 people from the audience):**
*   **What they said:**
*   **What changed, with the storyboard commit:**

## User test 2: near-final cut

*   **What they watched:** version one, the 89-second film with Ken Burns
    motion over the keyframes.
*   **What they said:**
    *   One tester found the video motion a bit laggy.
    *   The other testers said the narration should change, because the AI
        voice didn't sound right.
*   **What changed:** version two (`storyboard_v2.json`, commit `7813f7e`).
    *   **Motion:** the stepped, linear `zoompan` moves were replaced with
        eased, sub-pixel depth parallax, and the shots now dissolve into
        each other (EXPERIMENTS.md E11).
    *   **Narration:** ten of the 16 lines were reworded, and the delivery
        styles were rewritten (for example, "cheerful and excited" became
        "bright and eager"). The two voices stayed the same, because
        Gemini has only one Amharic male voice and the free tier allows
        about 20 lines a day (E6, F5).
    *   Version one stays on heritage.bebrook.co so the two cuts can be
        compared.

## Motion differences between exports

_Shots that move in 9:16 but not in 16:9, and why._
