import random

HOOKS = [
    "Most people don’t fear failure.",
    "You’re not stuck. You’re protected.",
    "This truth feels uncomfortable for a reason.",
    "Most people never notice this pattern.",
    "What you avoid is usually the answer."
]

CORES = [
    "They fear realizing they chose comfort over growth.",
    "Avoidance often disguises itself as intelligence.",
    "Familiar pain feels safer than unknown improvement.",
    "Most decisions are emotional, then justified later.",
    "Comfort is addictive because it removes responsibility."
]

CLOSERS = [
    "Once you see it, you can’t unsee it.",
    "That’s why it keeps repeating.",
    "That’s the trap nobody talks about.",
    "And that’s the uncomfortable part.",
    "That’s the cost of staying comfortable."
]

ONSCREEN = [
    ["Most people don’t fear failure",
     "They fear realization",
     "Comfort feels safe",
     "Until it traps you"],
    ["Avoidance feels intelligent",
     "Familiar feels safe",
     "Growth feels threatening",
     "That’s the pattern"]
]

def build_script():
    hook = random.choice(HOOKS)
    core = random.choice(CORES)
    close = random.choice(CLOSERS)

    return {
        "title": "An uncomfortable truth",
        "script": f"{hook} {core} {close}",
        "onscreen_text": random.choice(ONSCREEN),
        "hashtags": ["psychology", "truth", "mindset"]
    }
