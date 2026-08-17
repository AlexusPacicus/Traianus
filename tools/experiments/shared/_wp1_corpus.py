"""Shared WP1 corpus — three explicit categories for empirical validation."""
from collections.abc import Iterator


CATEGORY_A_TECHNICAL = [
    "The state vector v must be L2 normalized to unit length before projection onto the geodetic basis.",
    "Dual-key consolidation requires both the Topological Key and the Ethical Key to be satisfied simultaneously.",
    "The simplicial complex S_n is defined as the tuple of vertices V_n, edges E_n, and faces K_n.",
    "Every state transition in the manifold nodes table must be recorded as an append-only revision with increasing seq.",
    "The geodetic basis consists of eight axes derived from NSM primitives via farthest-point greedy selection.",
    "Projection variance sigma squared measures the dispersion of dot products across all basis axes.",
    "The dynamic threshold theta_dyn is calibrated by excluding self-projection terms where i equals j.",
    "Local adjacency E_n is computed via L2 distance between vectors with epsilon equal to zero point eight.",
    "Epoch provenance PROSTHETIC_NSM_V1 identifies the active seed epoch for all anchored coordinates.",
    "The ingest endpoint must reject non text plain content types at the zero-trust perimeter.",
    "Vector blobs are serialized as float64 byte arrays for deterministic persistence in SQLite.",
    "The operator token is required for all routes that mutate substrate state or expose telemetry.",
    "CORS origins must be enumerated explicitly without wildcard to prevent credentialed cross-origin attacks.",
    "The spectral processor encodes raw text to 384D vectors using all-MiniLM-L6-v2 with local files only.",
    "Action potential is derived from the projection variance without magic constants per ADR-005.",
    "The epsilon adjacency relation is purely observational and must not alter lifecycle states.",
    "Every database connection must run PRAGMA journal_mode equals WAL for write-ahead logging.",
    "Dimension mismatch is rejected when provider vector dimension exceeds geodetic baseline dimension.",
    "Idempotency keys ensure exactly-once ingestion semantics under concurrent requests.",
    "The farthest-point greedy algorithm selects basis axes to minimize maximum pairwise cosine similarity.",
    "Vertices in the manifold represent L2-normalized embeddings of external knowledge notes.",
    "Consolidation creates a new node revision without overwriting the original row per audit finding H4.",
    "The Topological Key is a provisional informational score based on spectral variance against the basis.",
    "Cross-epoch comparisons are prohibited without re-projection per epoch provenance constraints.",
    "The critical variance threshold is computed from cross-projections only excluding the diagonal.",
    "Refined entity projections are persisted from the validated Pydantic contract not from raw dicts.",
    "Telemetry error rows are append-only and excluded from epsilon adjacency computations.",
    "The manifold edges table supports tombstone state removed for append-only edge lifecycle tracking.",
    "Provider agnosticism means the control plane operates deterministically over any coordinate vector origin.",
    "Bitwise determinism is guaranteed only given identical input vectors and fixed model revision.",
    "The Sentence Transformer model is pinned to a specific revision hash for reproducibility.",
    "Null byte detection at the ingress perimeter prevents binary payload injection attacks.",
    "Strict UTF-8 decoding with errors equals strict rejects malformed payloads at the byte level.",
    "The active epoch is determined by the most recently created epoch provenance in geodesic axes.",
    "Logographic genesis expands the hyperspace dimension by appending a canonical orthogonal axis.",
    "Node existence validation prevents dangling edge creation in the forge relation endpoint.",
    "The CHECK constraint on lifecycle state restricts valid values to four operational states.",
    "Bootstrap extraction uses the anchor concept something as the first axis in the octagon basis.",
    "Revision sequences ensure monotonic append-only evolution of node and edge records.",
    "The repository enforces RFC 2119 compliance for all normative specifications and invariants.",
    "Historical vertices edges and simplicial faces in persistent storage are immutable per ADR-025.",
    "The spectral projection signature is computed as the dot product between the normalized vector and each axis.",
    "Variance inflation occurs when self-projection terms are included in threshold calibration per audit C1.",
    "The dual gate evaluates to consolidated only when both topological and ethical conditions are met.",
    "Cross-projection exclusion ensures the baseline variance reflects inter-axis dispersion not self-similarity.",
]


CATEGORY_B_CONVERSATIONAL = [
    "Hey did you see the email from Sarah about the meeting on Thursday afternoon?",
    "I think we should probably grab lunch at that new place near the corner sometime this week.",
    "Can you remind me what time the call starts tomorrow morning with the design team?",
    "The weather has been really nice lately perfect for walking to the office instead of taking the bus.",
    "I was wondering if you had a chance to look at the draft I sent over yesterday evening.",
    "Let me know when you are free to chat about the project timeline and next steps.",
    "Thanks for sending that over I will take a look first thing in the morning.",
    "We need to figure out who is going to handle the client presentation next Monday afternoon.",
    "I completely forgot about the deadline extension we discussed last week in the standup.",
    "Do you remember where we parked the car when we went to the conference downtown last month?",
    "The coffee machine on the third floor has been broken again since Tuesday I think.",
    "I was thinking we could maybe order pizza for the team lunch on Friday if that works for everyone.",
    "Can you pick up some milk on your way home I noticed we were running low this morning.",
    "I saw that movie you recommended last weekend it was actually pretty good overall.",
    "We should probably schedule a follow-up session to review the feedback from the usability study.",
    "The train was delayed again this morning so I ended up being about fifteen minutes late to the office.",
    "I was going to make a reservation for dinner but I was not sure what time everyone would be available.",
    "Did you get a chance to read the article I shared in the group chat yesterday about productivity?",
    "I think the new intern starts next week on Monday morning so we should prepare the onboarding materials.",
    "The printer in the marketing department has been making a weird noise again since last Thursday.",
    "We need to coordinate with the backend team about the API contract changes before the sprint review.",
    "I was wondering if it would be possible to push the demo back a couple of days to give us more time.",
    "The office plants need watering again I think whoever is responsible forgot to do it this week.",
    "Can you send me the link to that spreadsheet we were working on last Tuesday afternoon please?",
    "I was planning to leave early today to pick up my daughter from school so I will be offline after three.",
    "We should probably order more supplies for the kitchen the paper towels and coffee are almost out again.",
    "I was not sure if you had seen the message about the all hands meeting scheduled for next Friday.",
    "The wifi in the conference room has been really slow lately especially during the afternoon video calls.",
    "I was thinking about reorganizing the shared drive to make it easier to find the older project files.",
    "Can you let me know if you need any help with the onboarding docs before the new hire starts on Monday?",
    "I think we forgot to reply to that customer inquiry from last week it might still be sitting in the inbox.",
    "We should probably take a walk around the block after lunch it is such a nice day outside today.",
    "I was going to bring donuts for the morning meeting but I got stuck in traffic on the way to work.",
    "Do you know if the building management fixed the air conditioning issue on the second floor yet?",
    "I was wondering if we could reschedule the design review to Wednesday afternoon instead of Tuesday morning.",
    "The parking garage entrance is blocked again for construction so we need to use the side entrance today.",
    "I think I left my jacket in the meeting room on the fourth floor can you check if it is still there?",
    "We should probably send out a reminder about the team offsite planning survey before the end of the week.",
    "I was not sure whether to take the bus or drive today given the traffic report on the radio this morning.",
    "Can you ask Facilities about the broken blinds in the west conference room they have been like that for weeks?",
    "I think the new security badge system is finally working again after the update they did over the weekend.",
    "We should probably order some snacks for the afternoon workshop I think people will appreciate having something.",
    "I was planning to update the onboarding wiki but I got pulled into the production incident this morning instead.",
    "Did you happen to notice if the recycling bins were emptied yesterday they seem to be overflowing again.",
    "I was thinking we could carpool to the offsite next month to save on parking and gas money.",
    "The thermostat in the open office area has been set way too high again can someone talk to Facilities please?",
]


CATEGORY_C_NOISE = [
    "purple elephant dancing on the ceiling of a submarine sandwich factory at midnight",
    "quick sort algorithm banana republic fuzzy wuzzy was a bear had no hair",
    "the square root of yesterday is blue and tastes like quadratic equations on toast",
    "xyzqwk mnbvc lkjhg fdsap oiuyt rewq zx cvb nm lk jh gf ds a",
    "supercalifragilisticexpialidocious backwards spells something nobody really cares to memorize",
    "random walk hypothesis applied to the migration patterns of left handed staplers in spring",
    "colorless green ideas sleep furiously while the refrigerator hums a tune in B flat minor",
    "forty-two is the answer to everything according to a towel in the Andromeda galaxy",
    "the quick brown fox jumps over the lazy dog and then files a complaint with HR",
    "binary digits walking through a field of analog sunflowers at the speed of dark",
    "superposition of a cat that is both alive and slightly annoyed by the attention",
    "the entropy of a perfectly shuffled deck of cards equals approximately two hundred twenty-six bits",
    "morse code transmitted via semaphore flags during a thunderstorm in a library of whispers",
    "the mitochondria is the powerhouse of the cell according to every biology textbook ever written",
    "infinite monkeys typing Shakespeare eventually produce a grocery list instead of Hamlet",
    "the sound of one hand clapping echoes through an empty conference room on a Friday afternoon",
    "chaos theory suggests that a butterfly flapping its wings can cause a printer jam in the next room",
    "the angular momentum of a spinning pizza slice in zero gravity defies conventional culinary physics",
    "a sufficiently advanced technology is indistinguishable from a magic trick performed by a confused intern",
    "the spontaneous combination of unrelated phonemes produces neither meaning nor any discernible pattern",
]


ALL_CATEGORIES = {
    "A": CATEGORY_A_TECHNICAL,
    "B": CATEGORY_B_CONVERSATIONAL,
    "C": CATEGORY_C_NOISE,
}


MIN_PARAGRAPHS = 100
MIN_A, MIN_B, MIN_C = 40, 40, 20


def validate_corpus() -> None:
    total = sum(len(v) for v in ALL_CATEGORIES.values())
    assert total >= MIN_PARAGRAPHS, f"Corpus too small: {total} paragraphs."
    assert len(CATEGORY_A_TECHNICAL) >= MIN_A
    assert len(CATEGORY_B_CONVERSATIONAL) >= MIN_B
    assert len(CATEGORY_C_NOISE) >= MIN_C


def iter_corpus() -> Iterator[tuple[str, str]]:
    for label, paragraphs in ALL_CATEGORIES.items():
        for p in paragraphs:
            yield label, p
