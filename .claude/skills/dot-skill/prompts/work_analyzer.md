# Work Skill Analysis Prompt

## Task

You will receive **{name}**'s source material (documents, messages, emails, etc.).
Extract their work capabilities and methods for building the Work Skill.

**Principle: extract work-related content only; ignore small talk. Do not infer — write only what has evidence, otherwise mark "insufficient source material".**

---

## Universal Extraction Dimensions (apply to all roles)

### 1. Scope of Responsibility

Identify from the source material:
- Systems / modules / business lines / products they own
- Documents they maintain (API docs, wikis, runbooks...)
- Their responsibility boundaries (what is theirs, what is not)
- Project codenames and business terms they mention frequently

```
Output format:
Domain of ownership: [description]
Core systems: [list]
Maintained documents: [list]
Boundaries: [what they own / what they don't]
```

### 2. Workflow

Extract from task descriptions and meeting notes:
- Step-by-step handling when receiving a task
- Structural habits when writing plans / documents
- How they manage progress and handle deadlines
- How they handle exceptions / emergencies

```
Output format:
Receiving a task: [steps]
Writing a plan: [structure description]
Exception handling: [process]
```

### 3. Output Format Preferences

- Tables / lists / flow diagrams / plain text
- Conclusion up front vs. gradual buildup
- Document detail level (minimal / moderate / exhaustive)
- Reply / email style

```
Output format:
Document style: [description]
Detail level: [minimal / moderate / exhaustive]
```

### 4. Experience Knowledge Base

Experience-based judgments they expressed explicitly, pitfalls they hit, technical opinions (quote the original words directly):

```
- "[original words or summary]"
- "[original words or summary]"
```

---

## Role-Specific Extraction

Based on {name}'s role, focus on the matching dimensions:

---

### 🖥️ Backend Engineer / Server-Side Engineer

**Technical standards**:
- Tech stack (languages, frameworks, middleware)
- Naming conventions (API path style, variable/function naming)
- API design (response structure, error codes, pagination, idempotency)
- Database operation preferences (ORM vs raw SQL, transaction boundaries)
- Exception handling style

**Code Review focus**:
- CR issues they raise repeatedly (N+1, transactions, concurrency safety...)
- Their CR comment style (direct / tactful, [block]/[suggest] severity levels...)

**Deployment and operations**:
- Monitoring metrics they care about
- Production incident troubleshooting steps
- Change release process

---

### 🌐 Frontend Engineer

**Technical standards**:
- Tech stack (framework, state management, styling approach)
- Component splitting principles (when to split, when not to)
- Performance concerns (first screen, lazy loading, bundle size...)
- API invocation and error handling patterns

**Engineering practices**:
- Code-standard tooling (ESLint rules, Prettier config preferences)
- Test coverage requirements (attitude toward unit / integration tests)
- CR focus (attention to accessibility / responsiveness / compatibility)

---

### 🤖 Algorithm Engineer / ML Engineer

**Research and experiments**:
- Problem framing (how they decompose ML problems)
- Experiment design habits (baseline selection, ablation design)
- Metric definition preferences (attitude toward offline vs online metrics)
- Models / methodologies they habitually use

**Engineering implementation**:
- Training framework preferences
- Model deployment process
- Data processing standards

**Documents and conclusions**:
- How experiment reports are written (conclusion-heavy vs process-heavy)
- Papers or methodologies they cite

---

### 📱 Product Manager / Technical PM

**Requirements handling**:
- PRD structure and level of detail
- How user stories / requirement boundaries are defined
- How they align with engineering (review style, change process)

**Decision frameworks**:
- Prioritization method (RICE / MoSCoW / custom)
- Ratio of data-driven vs intuition
- How they handle conflicting requirements

**Deliverables**:
- Document types they produce (PRD / MRD / prototypes / competitive analysis)
- Prototyping tool preferences
- Level of involvement in analytics event tracking

---

### 🎨 Designer

**Design standards**:
- Design systems / component libraries they use
- Annotation style and delivery standards
- How strictly they require pixel-perfect implementation

**Workflow**:
- Steps from requirement to design solution
- How design walkthroughs / acceptance are done
- How they handle implementation-fidelity issues from the dev side

---

### 📊 Data Analyst

**Analysis methods**:
- Habitual analysis frameworks (funnel / cohort / A/B testing...)
- SQL style (terse / heavily commented)
- Data visualization preferences (chart type selection)

**Report style**:
- Ratio of conclusions vs data
- How strictly they practice "let the data speak"
- How they handle data anomalies / metric-definition disputes

---

## Output Requirements

- Language: write in the user's language
- Dimensions with no information: mark `(insufficient source material; appending related documents is recommended)`
- Conclusions backed by source text: quote the original words in quotation marks
- The output feeds directly into generating work.md — it must be concrete and actionable; never write vague phrasing like "possibly" or "tends to"
