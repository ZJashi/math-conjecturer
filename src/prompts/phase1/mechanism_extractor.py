PERSONA = '''
You are a world-class research mathematician who participates in formulating open problems and potential research directions.
You specialize in **Knowledge Base Construction** for mathematical discovery, identifying the key entities, their relationships, and the current boundaries of knowledge within a given mathematics paper.
'''

GOAL = '''
**GOAL**
Your task is to translate a structured Markdown summary of a mathematics paper into a knowledge base (called the **blackboard**) represented as an XML file. 
You will decompose the narrative summary into discrete entities (e.g., Theorems, Definitions, Dissatisfactions, Examples) and link them to create a "Mechanism Graph" of the paper's current state.
'''

INPUT_FORMAT = '''
**INPUT DATA**
You will receive a detailed paper summary in Markdown format.
'''
# TODO: We need to make sure that the summary preserves all the necessary information for this extraction task.

OUTPUT_FORMAT = '''
**OUTPUT FORMAT**
Output *only* an XML block wrapped in `<blackboard>...</blackboard>`. For simplicity, omit the XML declaration line (`<?xml version="1.0" encoding="UTF-8"?>`).
When writing LaTeX code, do not escape special XML characters or use CDATA sections. The XML format is for structure and readability only.
'''

XML_SCHEMA_AND_INSTRUCTIONS = '''
**XML SCHEMA & INSTRUCTIONS**

You must structure the XML into three logical layers based on the paper's content:

### 1. Layer: `<context>` (The Established Truth)
Extract items from the "Key Definitions" and "Main Results" sections of the summary.
* **Concepts:** Use `<definition>` or `<concept>` for key mathematical objects.
    * *Attributes:* `id` (e.g., "def:1"), `title`.
    * *Children:* `<content>` (LaTeX definition), `<impact>` (Why it matters).
* **Theorems:** Use `<theorem>`, `<lemma>`, or `<proposition>`.
    * *Attributes:* `id` (e.g., "thm:main"), `title`.
    * *Children:* `<content>` (Formal statement), `<impact>` (Significance).

### 2. Layer: `<motivation>` (The Friction)
Extract items from the "Boundaries," "Technical Obstructions," and "Sharpness" sections.
* **Dissatisfactions:** Create `<dissatisfaction>` elements for every limitation, obstruction, or missing generalization mentioned.
    * *Attributes:* `id` (e.g., "dis:1"), `title`, `source_refs` (Space-separated IDs of the theorems/definitions that are unsatisfactory).
    * *Children:*
        * `<desired_behavior>`: What *should* be true? (e.g., "Should hold for n > 2").
        * `<heuristic>`: Why is this a limitation? (e.g., "Current proof relies on compactness").
* **Examples:** Use `<counterexample>` or `<example>` if the summary describes specific cases that show sharpness.
    * *Attributes:* `id`, `title`.
    * *Children:* `<structure>` (The setup), `<actual_behavior>` (The result), `<lesson>`.

### 3. Layer: `<frontier>` (The Open Questions)
Extract items from the "Explicit Conjectures" section.
* **Existing Conjectures:** Use `<raised_conjecture>` for open problems *explicitly stated in the paper*.
    * *Attributes:* `id` (e.g., "conj:orig_1"), `title`.
    * *Children:* `<content>`, `<heuristic>` (intuition provided by authors), `<impact>`.
'''

RULES = '''
**CRITICAL RULES**
1.  **ID Generation:** Generate short, semantic IDs (e.g., `thm:main_bound`, `def:sobolev_space`, `dis:dimension_constraint`).
2.  **Linking:** Ensure `source_refs` in `<dissatisfaction>` point to valid IDs in `<context>`.
3.  **Fidelity:** Copy LaTeX math exactly from the summary. Do not summarize the math; transcribe it.
4.  **Completeness:** If the summary lists "Technical Obstructions," you *must* create a corresponding `<dissatisfaction>` node.

'''

# EXAMPLE = '''
# **EXAMPLE OUTPUT**
# ```xml
# <blackboard>
#   <context>
#     <definition id="def:metrics" title="Metric Space">
#       <content>$(X, d)$ is a metric space...</content>
#       <impact>Foundation for the main result.</impact>
#     </definition>
#     <theorem id="thm:main" title="Main Bound">
#       <content>For all compact $K$, $f(K) < \epsilon$.</content>
#       <impact>First polynomial bound for this case.</impact>
#     </theorem>
#   </context>
#   <motivation>
#     <dissatisfaction id="dis:compactness" title="Compactness Restriction" source_refs="thm:main">
#       <desired_behavior>Extend result to non-compact manifolds.</desired_behavior>
#       <heuristic>The covering argument fails without compactness.</heuristic>
#     </dissatisfaction>
#   </motivation>
#   <frontier>
#     <raised_conjecture id="conj:author_1" title="General Case">
#       <content>The bound holds for all complete manifolds.</content>
#       <impact>Would solve the classification problem.</impact>
#     </raised_conjecture>
#   </frontier>
# </blackboard>
# '''
#
#
# schema = [
#   {
#     "elements": ["concept", "notation", "definition", "lemma", "proposition", "theorem", "corollary", "remark"],
#     "attributes": ["id", "title"],
#     "child_elements": ["content", "impact"],
#     "optional_child_elements": ["heuristic"],
#     "description": "Same as in standard math"
#   },
#   {
#     "element": "raised_conjecture",
#     "attributes": ["id", "title"],
#     "child_elements": ["content", "heuristic", "impact"],
#     "description": "Open problems explicitly mentioned in the paper"
#   },
#   {
#     "element": "partial_result",
#     "attributes": ["id", "title"],
#     "child_elements": ["content", "heuristic", "impact"],
#     "description": "A weaker, special, or approximate case of a conjecture that appears provable with current methods"
#   },
#   {
#     "element": "content",
#     "description": "Precise and detailed statement in LaTeX"
#   },
#   {
#     "element": "heuristic",
#     "description": "Why you believe something is true, e.g., informal reasoning, scaling arguments, physical analogies, or intuition supporting a conjecture"
#   },
#   {
#     "element": "impact",
#     "description": "Why this matters: Describe how this motivates the conjecture and what new insight it introduces"
#   },
#   {
#     "element": "dissatisfaction",
#     "attributes": ["id", "title"],
#     "child_elements": ["source_element", "desired_behavior", "heuristic"],
#     "optional_child_elements": ["example", "counterexample"],
#     "description": "What is unsatisfactory about an existing result or a new proposal. Whenever possible, this should be supported by examples or counterexamples."
#   },
#   {
#     "element": ["example", "counterexample"],
#     "attributes": ["id", "title"],
#     "child_elements": ["structure", "desired_behavior", "actual_behavior", "lesson"],
#     "description": "The (counter)examples which illustrate dissatisfaction, motivate possible improvements, or demonstrate results/proposals."
#   },
#   {
#     "element": "source_element",
#     "description": "The id(s) of the element(s) from which the dissatisfaction arise"
#   },
#   {
#     "element": "structure",
#     "description": "The model and assumptions being considered in the (counter)example"
#   },
#   {
#     "element": "desired_behavior",
#     "attributes": [],
#     "children": [],
#     "description": "The conjectured improvement possible"
#   },
#   {
#     "element": "actual_behavior",
#     "attributes": [],
#     "children": [],
#     "description": "The actual behavior of the (counter)example; this might need to be solved by LLM"
#   },
#   {
#     "element": "vision",
#     "attributes": ["id", "title"],
#     "children": [],
#     "description": "The high-level narrative or \"big picture\" goal"
#   },
#   {
#     "element": "new_concept",
#     "attributes": ["id", "title"],
#     "children": ["content", "heuristic", "impact"],
#     "description": "New concepts which helps you state your proposal (maybe this is not helpful)"
#   },
#   {
#     "element": ["new_notation", "new_definition"],
#     "attributes": ["id", "title"],
#     "children": ["content", "impact"],
#     "description": "New notations or definitions which helps you state your proposal"
#   },
#   {
#     "element": "conjectured_lemma",
#     "attributes": ["id", "title"],
#     "children": ["content", "heuristic", "impact"],
#     "description": "Technical results you believe to be true that support conjectured major results. Give no proof."
#   },
#   {
#     "element": ["conjectured_proposition", "conjectured_theorem"],
#     "attributes": ["id", "title"],
#     "children": ["content", "heuristic", "impact"],
#     "description": "Major result you believe to be true but unproven. Give no proof."
#   },
#   {
#     "element": "analogy",
#     "attributes": ["id", "title"],
#     "children": ["source_object", "target_object", "mapping", "example", "impact", "dissatisfaction"],
#     "description": "Provide examples where the analogy partially holds, or describe toy/special cases supporting it"
#   },
#   {
#     "element": "source_object",
#     "attributes": [],
#     "children": [],
#     "description": "Object, structure, or phenomenon from the starting point (e.g., free entropy, log-Sobolev inequality, spectral gap)"
#   },
#   {
#     "element": "target_object",
#     "attributes": [],
#     "children": [],
#     "description": "Analogous object in your specialty (e.g., Lyapunov exponent, entropy dissipation, spectral radius)"
#   },
#   {
#     "element": "mapping",
#     "attributes": [],
#     "children": [],
#     "description": "Precise correspondence between source and target with clear theoretical justification; no vague analogies"
#   },
#   {
#     "element": "objective",
#     "attributes": [],
#     "children": [],
#     "description": "What a proposal tries to achieve; could be partial progress toward a grand vision"
#   },
#   {
#     "element": "roadmap",
#     "attributes": [],
#     "children": [],
#     "description": "Step-by-step plan to arrive at the objective"
#   },
#   {
#     "element": "progress",
#     "attributes": [],
#     "children": [],
#     "description": "Current progress toward completing a proposal"
#   },
#   {
#     "element": "challenge",
#     "attributes": [],
#     "children": [],
#     "description": "Obstruction faced when attempting to realize the roadmap"
#   }
# ]
#
#
# '''
# <ElementDefinitions>
#
#   <[Type] id="..." title="...">
#     <content> (LaTeX statement) </content>
#     <impact> (Why this matters/motivates conjecture) </impact>
#   </[Type]>
#
#   <[Type] id="..." title="...">
#     <content> (LaTeX statement) </content>
#     <heuristic> (Informal reasoning/intuition) </heuristic>
#     <impact> (Significance) </impact>
#   </[Type]>
#
#   <dissatisfaction id="..." title="...">
#     <source_element> (ID of the element causing dissatisfaction) </source_element>
#     <desired_behavior> (The conjectured improvement) </desired_behavior>
#     <heuristic> (Reasoning) </heuristic>
#     <example> ... </example>
#     <counterexample> ... </counterexample>
#   </dissatisfaction>
#
#   <[Type] id="..." title="...">
#     <structure> (Model/assumptions) </structure>
#     <desired_behavior> ... </desired_behavior>
#     <actual_behavior> (Actual behavior of this example) </actual_behavior>
#     <lesson> ... </lesson>
#   </[Type]>
#
#   <analogy id="..." title="...">
#     <source_object> (Starting point object) </source_object>
#     <target_object> (Object in your specialty) </target_object>
#     <mapping> (Precise correspondence) </mapping>
#     <example> ... </example>
#     <impact> ... </impact>
#     <dissatisfaction> ... </dissatisfaction> </analogy>
#
#   <objective> (What proposal tries to achieve) </objective>
#   <roadmap> (Step-by-step plan) </roadmap>
#   <progress> (Current status) </progress>
#   <challenge> (Obstructions) </challenge>
#   <vision id="..." title="..."> (High-level narrative) </vision>
#
# </ElementDefinitions>
# '''
#
#
# '''
# <?xml version="1.0" encoding="UTF-8"?>
# <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified">
#
#     <xs:element name="content" type="xs:string">
#         <xs:annotation><xs:documentation>Precise and detailed statement in LaTeX.</xs:documentation></xs:annotation>
#     </xs:element>
#
#     <xs:element name="heuristic" type="xs:string">
#         <xs:annotation><xs:documentation>Why you believe something is true; Informal reasoning, scaling arguments, physical analogies, or intuition.</xs:documentation></xs:annotation>
#     </xs:element>
#
#     <xs:element name="impact" type="xs:string">
#         <xs:annotation><xs:documentation>Why this matters: Describe how this motivates the conjecture and what new insight it introduces.</xs:documentation></xs:annotation>
#     </xs:element>
#
#     <xs:element name="source_element" type="xs:string"> <xs:annotation><xs:documentation>The id(s) of the element(s) from which the dissatisfaction arises.</xs:documentation></xs:annotation>
#     </xs:element>
#
#     <xs:element name="structure" type="xs:string">
#         <xs:annotation><xs:documentation>The model and assumptions being considered in the (counter)example.</xs:documentation></xs:annotation>
#     </xs:element>
#
#     <xs:element name="desired_behavior" type="xs:string">
#         <xs:annotation><xs:documentation>The conjectured improvement possible.</xs:documentation></xs:annotation>
#     </xs:element>
#
#     <xs:element name="actual_behavior" type="xs:string">
#         <xs:annotation><xs:documentation>The actual behavior of the (counter)example; this might need to be solved by LLM.</xs:documentation></xs:annotation>
#     </xs:element>
#
#     <xs:element name="lesson" type="xs:string"/>
#
#     <xs:complexType name="NamedEntity">
#         <xs:attribute name="id" type="xs:ID" use="required"/>
#         <xs:attribute name="title" type="xs:string" use="required"/>
#     </xs:complexType>
#
#     <xs:complexType name="StandardMathType">
#         <xs:complexContent>
#             <xs:extension base="NamedEntity">
#                 <xs:sequence>
#                     <xs:element ref="content"/>
#                     <xs:element ref="impact"/>
#                 </xs:sequence>
#             </xs:extension>
#         </xs:complexContent>
#     </xs:complexType>
#
#     <xs:complexType name="ConjectureType">
#         <xs:complexContent>
#             <xs:extension base="NamedEntity">
#                 <xs:sequence>
#                     <xs:element ref="content"/>
#                     <xs:element ref="heuristic"/>
#                     <xs:element ref="impact"/>
#                 </xs:sequence>
#             </xs:extension>
#         </xs:complexContent>
#     </xs:complexType>
#
#     <xs:complexType name="ExampleType">
#         <xs:complexContent>
#             <xs:extension base="NamedEntity">
#                 <xs:sequence>
#                     <xs:element ref="structure"/>
#                     <xs:element ref="desired_behavior"/>
#                     <xs:element ref="actual_behavior"/>
#                     <xs:element ref="lesson"/>
#                 </xs:sequence>
#             </xs:extension>
#         </xs:complexContent>
#     </xs:complexType>
#
#     <xs:complexType name="AnalogyType">
#         <xs:complexContent>
#             <xs:extension base="NamedEntity">
#                 <xs:sequence>
#                     <xs:element name="source_object" type="xs:string">
#                         <xs:annotation><xs:documentation>Identify the object, structure, or phenomenon from the start point.</xs:documentation></xs:annotation>
#                     </xs:element>
#                     <xs:element name="target_object" type="xs:string">
#                         <xs:annotation><xs:documentation>Identify the analogous object in your specialty.</xs:documentation></xs:annotation>
#                     </xs:element>
#                     <xs:element name="mapping" type="xs:string">
#                         <xs:annotation><xs:documentation>Precise correspondence between source and target with theoretical justification.</xs:documentation></xs:annotation>
#                     </xs:element>
#                     <xs:choice minOccurs="0" maxOccurs="unbounded">
#                         <xs:element name="example" type="ExampleType"/>
#                     </xs:choice>
#                     <xs:element ref="impact"/>
#                     <xs:element name="dissatisfaction" type="DissatisfactionType" minOccurs="0"/>
#                 </xs:sequence>
#             </xs:extension>
#         </xs:complexContent>
#     </xs:complexType>
#
#     <xs:complexType name="DissatisfactionType">
#         <xs:complexContent>
#             <xs:extension base="NamedEntity">
#                 <xs:sequence>
#                     <xs:element ref="source_element"/>
#                     <xs:element ref="desired_behavior"/>
#                     <xs:element ref="heuristic"/>
#                     <xs:element name="example" type="ExampleType" minOccurs="0"/>
#                     <xs:element name="counterexample" type="ExampleType" minOccurs="0"/>
#                 </xs:sequence>
#             </xs:extension>
#         </xs:complexContent>
#     </xs:complexType>
#
#     <xs:element name="MathematicalKnowledgeBase">
#         <xs:complexType>
#             <xs:choice maxOccurs="unbounded">
#                 <xs:element name="concept" type="StandardMathType"/>
#                 <xs:element name="notation" type="StandardMathType"/>
#                 <xs:element name="definition" type="StandardMathType"/>
#                 <xs:element name="lemma" type="StandardMathType"/>
#                 <xs:element name="proposition" type="StandardMathType"/>
#                 <xs:element name="theorem" type="StandardMathType"/>
#                 <xs:element name="corollary" type="StandardMathType"/>
#                 <xs:element name="remark" type="StandardMathType"/>
#
#                 <xs:element name="raised_conjecture" type="ConjectureType"/>
#                 <xs:element name="partial_result" type="ConjectureType"/>
#
#                 <xs:element name="dissatisfaction" type="DissatisfactionType"/>
#                 <xs:element name="example" type="ExampleType"/>
#                 <xs:element name="counterexample" type="ExampleType"/>
#
#                 <xs:element name="vision">
#                     <xs:complexType>
#                         <xs:complexContent>
#                             <xs:extension base="NamedEntity">
#                                 <xs:sequence><xs:element name="narrative" type="xs:string"/></xs:sequence>
#                             </xs:extension>
#                         </xs:complexContent>
#                     </xs:complexType>
#                 </xs:element>
#
#                 <xs:element name="new_concept" type="ConjectureType"/>
#                 <xs:element name="new_notation" type="StandardMathType"/>
#                 <xs:element name="new_definition" type="StandardMathType"/>
#
#                 <xs:element name="conjectured_lemma" type="ConjectureType"/>
#                 <xs:element name="conjectured_proposition" type="ConjectureType"/>
#                 <xs:element name="conjectured_theorem" type="ConjectureType"/>
#
#                 <xs:element name="analogy" type="AnalogyType"/>
#
#                 <xs:element name="objective" type="xs:string"/>
#                 <xs:element name="roadmap" type="xs:string"/>
#                 <xs:element name="progress" type="xs:string"/>
#                 <xs:element name="challenge" type="xs:string"/>
#
#             </xs:choice>
#         </xs:complexType>
#     </xs:element>
#
# </xs:schema>
# '''


# =======================================================================
MECHANISM_EXTRACTOR_SYSTEM_PROMPT = PERSONA + GOAL + INPUT_FORMAT + OUTPUT_FORMAT + XML_SCHEMA_AND_INSTRUCTIONS + RULES
MECHANISM_EXTRACTOR_USER_PROMPT = '''
[MARKDOWN PAPER SUMMARY]
{paper_summary}

[YOUR OUTPUT]
'''