## Preface — Position of the Pairing Engine within the Project

The pairing engine presented in this document constitutes the application layer of the Portuguese Wine Database project.  
While the database models Portuguese wine through sensory structure and producer-grounded data, the pairing system operationalizes this model by translating wine behaviour into gastronomic compatibility decisions.

Rather than relying on probabilistic recommendation or flavour similarity, the engine applies an explicit rule framework derived from oenogastronomic principles. Wines and dishes are both represented as structured entities: wines through perceived structural attributes (acidity, tannin, body, sweetness, and finish), and dishes through cooking method, texture, and dominant interaction factors. Pairing outcomes therefore emerge from deterministic interaction rules that remain transparent and explainable.

This document evaluates the pairing engine not as software implementation alone, but as a reasoning model built upon the structural ontology established by the database. The objective is to assess whether the pairing theory encoded in the rules accurately reflects the behavioural insights revealed by the completed wine dataset.

# Portuguese Wine Database — Pairing Engine Audit  
## Structural Assessment and Alignment with the Wine DB

---

# 1. Executive Assessment

The pairing system is architecturally strong and conceptually coherent.  
It operates not as a recommendation engine but as a:

> **rule-driven structural gastronomy model**

Its design is deterministic, explainable, and aligned with the philosophy of the Portuguese Wine Database, where wines are modeled through **behavioural structure** rather than aroma description or reputation.

However, analysis shows that the pairing rules currently reflect an **earlier interpretative phase** of the project.

- The database has evolved toward a structural understanding centered on equilibrium, texture, and persistence.
- The pairing rules remain primarily calibrated around acidity-driven pairing logic.

In short:

Architecture ✓ mature
Gastronomic logic ✓ correct
Coverage ⚠ incomplete
Bias ⚠ acidity-centric / white-leaning


Nothing is fundamentally broken; the rules now need to evolve to match the discoveries produced by the database itself.

---

# 2. Structural Design Strengths

## 2.1 Separation of Concerns

The pairing pipeline is cleanly structured:

Wine DB (structure)
↓
pairing rules (oenogastronomic theory)
↓
dish ontology (food structure)
↓
pairing generator
↓
explainable output


Each layer performs a distinct role, allowing reasoning to remain transparent.

---

## 2.2 Structural Rather Than Aromatic Pairing

Pairing decisions rely on:

- acidity
- tannins
- body
- sweetness
- finish
- wine type

This mirrors the database’s philosophy and avoids subjective flavor matching.

---

## 2.3 Hard Filters Before Scoring

The system correctly separates:

hard_filters → eliminate impossibilities
rules → score compatibilities


This encodes culinary constraints rather than preference.  
Examples such as limiting tannins for delicate dishes reflect real gastronomic physics.

---

## 2.4 Conflict Modelling

Rules explicitly encode pairing failures (e.g., tannic reds with delicate fish).  
This is a major strength rarely present in pairing systems.

---

## 2.5 Dish Ontology Quality

Dishes are modeled as interaction problems through:

- dominant factors
- cooking method
- texture
- flavor behaviour
- meal progression (“meal arcs”).

This allows temporal pairing logic and narrative sequencing rather than isolated matches.

---

# 3. Structural Bias Emerging from Rule Distribution

## 3.1 White Wine Overrepresentation

A large number of rules activate for tags such as:

light
raw
citrus
umami
steamed
delicate


These occur frequently across dishes, causing white wines to accumulate scoring opportunities.

Red wines, by contrast, are mostly triggered only by:

- fatty meat
- heavy stews
- robust preparations.

This encodes an implicit assumption:

white wine = versatile
red wine = heavy-food specialist


The database demonstrates this assumption is incomplete.

---

## 3.2 Missing Category: Fresh Structured Reds

The database revealed a major Portuguese category:

medium body
acidity 6–7
tannins 5–6
long finish


Examples include classical Dão wines, Baga, Jaen, restrained Alentejo reds, and some Douro blends.

These wines pair successfully with:

- grilled fish
- mushrooms
- fermented broths
- soy-based preparations
- umami-dominant dishes.

Current rules rarely allow these wines to surface.

This represents the largest conceptual gap in the system.

---

# 4. Underused Structural Dimensions

## 4.1 Texture

Although dishes include texture descriptors (silky, creamy, crunchy, robust), rules rarely use them.

This omits one of Portugal’s strongest pairing assets:

- lees-aged whites
- talha wines
- oxidative Madeira
- textured field blends.

Texture interaction should become an active pairing dimension.

---

## 4.2 Persistence (Finish)

Portuguese wine frequently expresses long finish persistence, yet rules primarily reward acidity rather than persistence matching.

Long finishes often pair with layered or lingering dishes independently of weight.

---

# 5. Regional Bonus Misalignment

The rule granting regional affinity bonuses introduces geographic preference.

The wine database demonstrated structural continuity across regions rather than stylistic isolation.  
Maintaining regional scoring risks reintroducing bias the project intentionally removed.

Recommendation:
- weaken or remove regional bonuses as scoring factors.

---

# 6. Fortified Wines Underrepresented

Fortified wines are largely confined to dessert roles.

However, structural analysis shows broader gastronomic potential:

- dry Madeira with umami broths,
- Verdelho with fried dishes,
- oxidative styles with mushrooms and aged flavors.

The rule set currently underutilizes these possibilities.

---

# 7. Missing Conflict Dimension

A significant omission is the interaction between alcohol and spice.

High-alcohol wines paired with spicy dishes can amplify heat perception.  
A structural conflict rule addressing alcohol vs spice is recommended.

---

# 8. Rule Mechanics: Accumulation Bias

Scoring currently sums multiple compatible rules.

Dishes with many mild tags can trigger several rules simultaneously, rewarding tag density rather than pairing necessity.

Long-term improvement would treat rules as dimensions:

- acidity interaction
- texture compatibility
- tannin conflict
- sweetness balance
- aromatic reinforcement.

Only the strongest rule per dimension should dominate scoring.

---

# 9. What the Engine Currently Favors

Implicitly favored:

- high-acidity Atlantic whites
- sparkling wines
- light aromatic profiles.

Neutral:

- balanced equilibrium wines.

Underrepresented:

- fresh structured reds
- talha wines
- gastronomic Madeira styles.

This imbalance reflects historical pairing assumptions rather than database evidence.

---

# 10. System Completeness

All required components are now observable:

- compiled wine structures
- dish ontology
- pairing rules
- scoring engine
- generated outputs.

No additional files are required for conceptual evaluation.

---

# 11. Core Insight

The pairing rules describe traditional sommelier teaching.  
The database describes observed structural behaviour.

The next evolution of the system is therefore:

> moving from inherited pairing doctrine toward empirically derived pairing logic.

---

# 12. Primary Recommendation

Introduce a new rule family representing fresh structured reds:

wine:
type = red
acidity ≥ 6
tannins ≤ 6
body = medium or medium-full

food_tags:
grilled
mushroom
umami
fermented
soy_based


This single addition would substantially rebalance outputs and align pairings with the structural discoveries of the Portuguese Wine Database.

---

# 13. Conclusion

The pairing engine is already sophisticated, explainable, and philosophically aligned with the database.

Its current limitation is not technical but evolutionary:  
the rules still encode a freshness-centric interpretation of Portuguese wine, while the database now reveals a broader structural ecosystem defined equally by balance, texture, and persistence.

Updating the rule layer to reflect these findings will allow the pairing system to fully express the analytical power of the database itself.

## Conclusion — Implications of the Audit

The assessment demonstrates that the pairing engine is conceptually sound and closely aligned with the structural philosophy of the Portuguese Wine Database. Its deterministic and explainable architecture successfully transforms wine structure into gastronomic reasoning, avoiding the opacity common to recommendation systems.

The audit further shows that recent developments in the database have expanded the understanding of Portuguese wine behaviour beyond traditional acidity-centered pairing assumptions. The primary adjustments identified therefore concern the evolution of pairing theory rather than corrections to the underlying data model. The database itself remains structurally complete; the rule layer must now incorporate equilibrium, texture, and persistence as pairing dimensions alongside freshness.

This outcome illustrates an important methodological result: empirical modelling of wine behaviour can refine inherited gastronomic doctrine. The pairing engine thus becomes not only a practical tool but also an analytical framework through which traditional pairing concepts can be tested, challenged, and progressively improved.
