import pptxgen from 'pptxgenjs';

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'Taxxa GraphRAG team';
pptx.subject = 'Agentic GraphRAG for Finnish tax law';
pptx.title = 'Agentic GraphRAG for Finnish Tax Law';
pptx.company = 'Prompt Finance Hackathon 2026';
pptx.lang = 'en-US';
pptx.theme = {
  headFontFace: 'Playfair Display',
  bodyFontFace: 'Aptos',
  lang: 'en-US',
};

const C = {
  ivory: 'FAF9F5',
  paper: 'F4EFE7',
  line: 'E8E6DC',
  lineDark: 'D8D3C7',
  ink: '141413',
  charcoal: '30302E',
  muted: '6F6C63',
  soft: 'B0AEA5',
  clay: 'C96442',
  clayDark: '8D3E28',
  olive: '76715F',
  white: 'FFFFFF',
};

const W = 13.333;
const H = 7.5;
const M = 0.58;

const serif = 'Playfair Display';
const sans = 'Aptos';
const mono = 'Cascadia Mono';

function slideBase(slide, section, page) {
  slide.background = { color: C.ivory };
  slide.addShape(pptx.ShapeType.rect, {
    x: 0,
    y: 0,
    w: W,
    h: 0.18,
    fill: { color: C.paper },
    line: { color: C.paper },
  });
  slide.addText('TAXXA GRAPH RAG', {
    x: M,
    y: 0.32,
    w: 2.4,
    h: 0.18,
    fontFace: sans,
    fontSize: 7.5,
    bold: true,
    color: C.muted,
    charSpace: 1.4,
    margin: 0,
  });
  slide.addText('Prompt Finance Hackathon 2026', {
    x: W - 3.25,
    y: 0.32,
    w: 2.65,
    h: 0.18,
    fontFace: sans,
    fontSize: 7.5,
    color: C.muted,
    align: 'right',
    margin: 0,
  });
  slide.addShape(pptx.ShapeType.line, {
    x: M,
    y: 0.64,
    w: W - M * 2,
    h: 0,
    line: { color: C.line, width: 0.75 },
  });
  slide.addText(section, {
    x: M,
    y: H - 0.38,
    w: 3.4,
    h: 0.16,
    fontFace: sans,
    fontSize: 7.5,
    color: C.muted,
    margin: 0,
  });
  slide.addText(String(page).padStart(2, '0'), {
    x: W - 1.05,
    y: H - 0.42,
    w: 0.45,
    h: 0.22,
    fontFace: serif,
    fontSize: 11,
    color: C.muted,
    align: 'right',
    margin: 0,
  });
}

function kicker(slide, text, x, y, color = C.clay) {
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y: y + 0.07,
    w: 0.28,
    h: 0.035,
    fill: { color },
    line: { color },
  });
  slide.addText(text.toUpperCase(), {
    x: x + 0.4,
    y,
    w: 3.4,
    h: 0.18,
    fontFace: sans,
    fontSize: 7.5,
    bold: true,
    color,
    charSpace: 1.2,
    margin: 0,
  });
}

function title(slide, text, x, y, w, h, size = 32, color = C.ink) {
  slide.addText(text, {
    x,
    y,
    w,
    h,
    fontFace: serif,
    fontSize: size,
    bold: false,
    color,
    breakLine: false,
    fit: 'shrink',
    margin: 0,
    breakLine: false,
  });
}

function body(slide, text, x, y, w, h, opts = {}) {
  slide.addText(text, {
    x,
    y,
    w,
    h,
    fontFace: opts.fontFace || sans,
    fontSize: opts.size || 12.5,
    color: opts.color || C.muted,
    bold: !!opts.bold,
    margin: opts.margin ?? 0,
    fit: 'shrink',
    breakLine: false,
  });
}

function clayPill(slide, text, x, y, w) {
  slide.addShape(pptx.ShapeType.roundRect, {
    x,
    y,
    w,
    h: 0.33,
    rectRadius: 0.04,
    fill: { color: C.paper },
    line: { color: C.lineDark, width: 0.8 },
  });
  slide.addText(text, {
    x: x + 0.12,
    y: y + 0.08,
    w: w - 0.24,
    h: 0.12,
    fontFace: sans,
    fontSize: 7.5,
    bold: true,
    color: C.muted,
    align: 'center',
    charSpace: 0.4,
    margin: 0,
  });
}

function proofBox(slide, label, value, note, x, y, w, h, accent = false) {
  slide.addShape(pptx.ShapeType.rect, {
    x,
    y,
    w,
    h,
    fill: { color: accent ? C.charcoal : C.white, transparency: 0 },
    line: { color: accent ? C.charcoal : C.line, width: 0.8 },
  });
  body(slide, label.toUpperCase(), x + 0.22, y + 0.22, w - 0.44, 0.2, {
    size: 7.2,
    bold: true,
    color: accent ? C.soft : C.muted,
  });
  title(slide, value, x + 0.22, y + 0.58, w - 0.44, 0.6, 27, accent ? C.ivory : C.ink);
  body(slide, note, x + 0.22, y + 1.25, w - 0.44, h - 1.45, {
    size: 9.6,
    color: accent ? C.soft : C.muted,
  });
}

// 01 Cover
{
  const s = pptx.addSlide();
  slideBase(s, 'cover', 1);
  kicker(s, 'Agentic tax research', 0.72, 1.05);
  title(s, 'GraphRAG that can\nfollow the law, not\njust retrieve text.', 0.72, 1.55, 8.25, 2.35, 38);
  body(
    s,
    'A multi-agent system for Finnish accounting and tax questions: structure-aware retrieval, typed graph traversal, claim verification, and source-grounded answers.',
    0.78,
    4.28,
    6.8,
    0.62,
    { size: 13.3, color: C.muted },
  );
  s.addShape(pptx.ShapeType.rect, {
    x: 9.55,
    y: 1.06,
    w: 2.9,
    h: 5.36,
    fill: { color: C.charcoal },
    line: { color: C.charcoal },
  });
  body(s, 'Hosted by', 9.95, 1.48, 1.8, 0.18, { size: 7.5, color: C.soft, bold: true });
  title(s, 'Aalto\nUniversity', 9.95, 1.82, 1.95, 0.92, 22, C.ivory);
  s.addShape(pptx.ShapeType.line, { x: 9.95, y: 3.15, w: 1.7, h: 0, line: { color: C.clay, width: 1.2 } });
  body(s, 'Challenge by', 9.95, 3.52, 1.8, 0.18, { size: 7.5, color: C.soft, bold: true });
  title(s, 'Taxxa\nAI Oy', 9.95, 3.86, 1.95, 0.78, 22, C.ivory);
  body(s, 'May 2026', 9.95, 5.7, 1.5, 0.2, { size: 8.4, color: C.soft });
  clayPill(s, 'Python', 0.78, 6.05, 0.9);
  clayPill(s, 'NetworkX', 1.82, 6.05, 1.15);
  clayPill(s, 'LLM agents', 3.12, 6.05, 1.2);
}

// 02 Problem
{
  const s = pptx.addSlide();
  slideBase(s, 'problem', 2);
  kicker(s, 'Why naive RAG fails', 0.72, 0.96);
  title(s, 'Legal research fails when\nstructure is flattened.', 0.72, 1.32, 5.9, 1.3, 31);
  body(
    s,
    'Finnish tax answers are usually not in one paragraph. They live across statutes, guidance, amendments, definitions, and exceptions.',
    0.78,
    2.9,
    4.9,
    0.7,
    { size: 12.5 },
  );
  const rows = [
    ['01', 'Chunking cuts logic', 'A rule and its exception often land in different windows.'],
    ['02', 'References stay inert', '"See section 102" is just text unless the retriever can follow it.'],
    ['03', 'Time matters', 'A superseded rule can look semantically closer than the current rule.'],
  ];
  rows.forEach((r, i) => {
    const y = 4.0 + i * 0.72;
    body(s, r[0], 0.78, y + 0.02, 0.42, 0.14, { size: 8, color: C.clay, bold: true });
    body(s, r[1], 1.32, y, 1.85, 0.18, { size: 10.2, color: C.ink, bold: true });
    body(s, r[2], 3.35, y, 3.0, 0.26, { size: 9.5, color: C.muted });
    s.addShape(pptx.ShapeType.line, { x: 0.78, y: y + 0.45, w: 5.65, h: 0, line: { color: C.line, width: 0.6 } });
  });
  s.addShape(pptx.ShapeType.rect, {
    x: 7.35,
    y: 1.18,
    w: 4.95,
    h: 4.95,
    fill: { color: C.paper },
    line: { color: C.lineDark, width: 0.8 },
  });
  title(s, '"What withholding-tax rate applies to a foreign specialist with key-personnel status?"', 7.78, 1.68, 3.95, 1.5, 19, C.ink);
  body(s, 'A correct answer needs a statute, a Vero interpretation, and the amendment that changed the rate and validity window.', 7.8, 3.55, 3.85, 0.75, { size: 12 });
  s.addShape(pptx.ShapeType.line, { x: 7.8, y: 4.72, w: 3.55, h: 0, line: { color: C.clay, width: 1.1 } });
  body(s, 'Top-k alone returns proximity. The task needs provenance.', 7.8, 5.1, 3.55, 0.28, { size: 10, color: C.clayDark, bold: true });
}

// 03 Thesis / approach
{
  const s = pptx.addSlide();
  slideBase(s, 'approach', 3);
  kicker(s, 'System thesis', 0.72, 0.96);
  title(s, 'Parse the corpus into a map,\nthen let agents walk it with intent.', 0.72, 1.32, 7.0, 1.35, 30);
  const stages = [
    ['Parse', 'Respect publisher structure: titles, sections, paragraphs, dates.'],
    ['Connect', 'Create typed edges for interprets, amends, cites, references, same-doc context.'],
    ['Retrieve', 'Use vector and keyword search to find entry points, then expand graph neighborhoods.'],
    ['Verify', 'Audit each claim against retrieved source passages before final answer.'],
  ];
  stages.forEach((st, i) => {
    const x = 0.82 + i * 3.0;
    s.addShape(pptx.ShapeType.line, { x, y: 3.05, w: 2.38, h: 0, line: { color: i === 3 ? C.clay : C.lineDark, width: i === 3 ? 1.4 : 0.8 } });
    body(s, `0${i + 1}`, x, 3.32, 0.55, 0.16, { size: 8, color: C.clay, bold: true });
    title(s, st[0], x, 3.62, 1.8, 0.34, 15, C.ink);
    body(s, st[1], x, 4.15, 2.34, 0.75, { size: 9.8 });
  });
  s.addShape(pptx.ShapeType.rect, { x: 0.78, y: 5.56, w: 11.7, h: 0.72, fill: { color: C.charcoal }, line: { color: C.charcoal } });
  body(s, 'Design principle', 1.08, 5.78, 1.55, 0.12, { size: 7.5, color: C.soft, bold: true });
  body(s, 'The graph is not decoration. It is how the system turns legal cross-references into retrieval actions.', 2.72, 5.72, 7.9, 0.22, { size: 11.3, color: C.ivory });
}

// 04 Pipeline
{
  const s = pptx.addSlide();
  slideBase(s, 'pipeline', 4);
  kicker(s, 'Agent loop', 0.72, 0.96);
  title(s, 'Six roles, one contract:\nanswer only what can be checked.', 0.72, 1.32, 6.6, 1.25, 30);
  const agents = [
    ['Clarifier', 'tax year, entity type, missing context'],
    ['Planner', '2-4 sub-queries with Finnish legal terms'],
    ['Retriever', 'vector + keyword + typed graph expansion'],
    ['Generator', 'draft answer with inline citations'],
    ['Auditor', 'fact, logic, completeness checks'],
    ['Confidence', 'score and caveat if evidence is weak'],
  ];
  agents.forEach((a, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const x = 0.82 + col * 4.0;
    const y = 3.1 + row * 1.45;
    const active = i === 2 || i === 4;
    s.addShape(pptx.ShapeType.rect, {
      x,
      y,
      w: 3.55,
      h: 1.02,
      fill: { color: active ? C.paper : C.white },
      line: { color: active ? C.clay : C.line, width: active ? 1.3 : 0.8 },
    });
    body(s, String(i + 1).padStart(2, '0'), x + 0.2, y + 0.16, 0.38, 0.12, { size: 7.4, color: C.clay, bold: true });
    title(s, a[0], x + 0.72, y + 0.14, 1.65, 0.25, 13, C.ink);
    body(s, a[1], x + 0.72, y + 0.5, 2.45, 0.28, { size: 8.8 });
  });
  body(s, 'Retry path: unverified claims become new retrieval queries, not hidden caveats.', 0.82, 6.22, 6.8, 0.22, { size: 10.3, color: C.clayDark, bold: true });
}

// 05 Graph proof
{
  const s = pptx.addSlide();
  slideBase(s, 'graph proof', 5);
  kicker(s, 'Typed graph', 0.72, 0.96);
  title(s, 'The graph encodes what a\nlegal researcher would follow.', 0.72, 1.32, 6.5, 1.24, 29);
  const edges = [
    ['interprets', 'Vero guidance -> Finlex statute'],
    ['amends', 'new rule -> previous provision'],
    ['cites', 'case law -> statute'],
    ['shared_ref', 'documents discussing the same section'],
    ['same_doc', 'surrounding paragraphs and headings'],
  ];
  edges.forEach((e, i) => {
    const y = 3.05 + i * 0.53;
    body(s, e[0], 0.82, y, 1.23, 0.14, { size: 8.4, color: C.clayDark, bold: true, fontFace: mono });
    body(s, e[1], 2.25, y, 3.15, 0.16, { size: 9.8, color: C.ink });
    s.addShape(pptx.ShapeType.line, { x: 0.82, y: y + 0.32, w: 5.15, h: 0, line: { color: C.line, width: 0.55 } });
  });
  proofBox(s, 'Nodes', '994K', 'Document structure becomes addressable evidence.', 7.05, 1.34, 1.55, 1.55, true);
  proofBox(s, 'Edges', '957K', 'Traversal can explain why a source was retrieved.', 8.8, 1.34, 1.55, 1.55);
  proofBox(s, 'Embedded', '240K', 'Filtered entry points keep retrieval tractable.', 10.55, 1.34, 1.55, 1.55);
  s.addShape(pptx.ShapeType.rect, { x: 7.05, y: 3.55, w: 5.05, h: 1.95, fill: { color: C.paper }, line: { color: C.lineDark, width: 0.8 } });
  body(s, 'Example walk', 7.4, 3.9, 1.2, 0.14, { size: 7.5, bold: true, color: C.clay });
  title(s, 'Vero hit -> Finlex law -> amendment -> cited answer', 7.4, 4.22, 3.95, 0.42, 15, C.ink);
  body(s, 'The result is not just a better passage. It is a chain of accountable evidence.', 7.4, 4.78, 3.95, 0.3, { size: 9.8 });
}

// 06 Results
{
  const s = pptx.addSlide();
  slideBase(s, 'evaluation', 6);
  kicker(s, 'Measured outcome', 0.72, 0.96);
  title(s, 'On 83 graded questions,\nthe system answers every time.', 0.72, 1.32, 6.6, 1.25, 30);
  proofBox(s, 'Key facts coverage', '70%', 'Rates, thresholds, dates, and required facts recovered from the corpus.', 0.82, 3.08, 3.2, 2.15, true);
  proofBox(s, 'Citation rate', '90.4%', 'Most answers include document-level traceability for claims.', 4.28, 3.08, 3.2, 2.15);
  proofBox(s, 'Answer rate', '100%', 'The agent always produces an answer, with caveats when confidence is low.', 7.74, 3.08, 3.2, 2.15);
  s.addShape(pptx.ShapeType.line, { x: 0.82, y: 5.82, w: 10.1, h: 0, line: { color: C.lineDark, width: 0.8 } });
  body(s, 'Takeaway', 0.82, 6.1, 0.9, 0.14, { size: 7.5, bold: true, color: C.clay });
  body(s, 'The main gain is not answer volume. It is making each answer inspectable enough for tax research.', 1.82, 6.06, 7.15, 0.22, { size: 10.8, color: C.ink });
}

// 07 Decisions
{
  const s = pptx.addSlide();
  slideBase(s, 'trade-offs', 7);
  kicker(s, 'Implementation choices', 0.72, 0.96);
  title(s, 'We chose boring pieces\nwhere boring made the system ship.', 0.72, 1.32, 6.7, 1.25, 30);
  const decisions = [
    ['Embeddings', 'bge-m3 -> e5-small', 'Faster iteration while preserving multilingual retrieval quality.'],
    ['Reranking', 'cross-encoder -> LLM', 'Better Finnish handling and less model plumbing.'],
    ['Traversal', 'blind BFS -> typed walk', 'Edge type decides what context is worth expanding.'],
    ['Agents', 'single call -> verified loop', 'Slower, but catches unsupported claims before delivery.'],
  ];
  decisions.forEach((d, i) => {
    const y = 3.1 + i * 0.74;
    body(s, d[0], 0.82, y, 1.35, 0.14, { size: 8.3, color: C.clayDark, bold: true });
    title(s, d[1], 2.4, y - 0.05, 2.4, 0.22, 13.5, C.ink);
    body(s, d[2], 5.28, y, 5.55, 0.16, { size: 9.8 });
    s.addShape(pptx.ShapeType.line, { x: 0.82, y: y + 0.42, w: 10.4, h: 0, line: { color: C.line, width: 0.55 } });
  });
  s.addShape(pptx.ShapeType.rect, { x: 8.95, y: 1.08, w: 2.95, h: 1.15, fill: { color: C.charcoal }, line: { color: C.charcoal } });
  body(s, 'Hackathon principle', 9.24, 1.38, 1.6, 0.12, { size: 7.2, color: C.soft, bold: true });
  body(s, 'Working, grounded, explainable beats elaborate and unfinished.', 9.24, 1.68, 2.15, 0.26, { size: 9.8, color: C.ivory });
}

// 08 Close
{
  const s = pptx.addSlide();
  slideBase(s, 'close', 8);
  title(s, 'Thank you.', 0.72, 1.82, 4.8, 0.76, 42);
  body(s, 'Questions? The graph schema is the interesting part.', 0.78, 3.0, 5.2, 0.25, { size: 14, color: C.muted });
  s.addShape(pptx.ShapeType.line, { x: 0.78, y: 3.72, w: 3.2, h: 0, line: { color: C.clay, width: 1.1 } });
  body(s, 'github.com/Jiarun-han/Agentic-GraphRAG-for-Finnish-tax-law', 0.78, 4.18, 6.2, 0.22, { size: 9.6, color: C.ink, bold: true });
  const stack = ['Python', 'NetworkX', 'DeepSeek V4', 'e5-small', 'FastAPI', 'React'];
  stack.forEach((t, i) => clayPill(s, t, 0.78 + i * 1.42, 5.4, 1.08));
  s.addShape(pptx.ShapeType.rect, { x: 8.15, y: 1.25, w: 3.6, h: 4.7, fill: { color: C.paper }, line: { color: C.lineDark, width: 0.8 } });
  kicker(s, 'Final answer contract', 8.55, 1.72);
  title(s, 'Cited.\nChecked.\nCurrent.', 8.55, 2.25, 2.3, 1.45, 27);
  body(s, 'A legal answer should show its route through the source material. That is the product promise.', 8.58, 4.25, 2.38, 0.55, { size: 11.2 });
}

await pptx.writeFile({ fileName: 'presentation/taxxa-claude-playfair.pptx' });
console.log('Written: presentation/taxxa-claude-playfair.pptx');
