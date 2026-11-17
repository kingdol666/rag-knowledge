"""Increase finished-size lettering in the editable KBS architecture diagrams."""
from pathlib import Path
from xml.etree import ElementTree as ET
import re

root = Path(__file__).resolve().parent / 'kbs_revision_20261112'
replacements = {
    'fig1_architecture.drawio': {
        'subtitle': 'Web, agent and retrieval services share auditable state',
        'nuxt': 'Nuxt server\nProxy and file operations',
        'fastapi': 'FastAPI\nAsync parse tasks',
        'mineru': 'MinerU worker\nDynamic port',
        'mcp': 'MCP server\nHTTP and local reads',
        'ingest': 'Ingest and split',
        'lifecycle': 'Lifecycle audit',
        'search': 'Hybrid search',
        'gate': 'Optional Laya gate',
        'docstore': 'Document files\nMarkdown and assets',
        'registry': 'Registries\nTree and KB YAML',
        'indices': 'Search indices\nVectors and BM25',
        'graph': 'Knowledge graph\nNeo4j navigation',
        'footer': 'Services share state; indexing and evidence judging are separate operations.',
        'state_label': 'SHARED STATE',
    },
    'fig2_workflow.drawio': {
        'subtitle': 'Agent placement, indexing and optional evidence judging',
        'ingest_step_0': 'Source files\nPDF, Office, scans',
        'ingest_step_1': 'Parse and check\nOCR, structure',
        'ingest_step_2': 'Read and route\nAgent selects KB',
        'ingest_step_3': 'Save state\nFiles and registries',
        'ingest_step_4': 'Index and probe\nEntry dependent',
        'placement_note': 'Agent selects the destination; the API stores the result.',
        'shared_state': 'Shared state: files, registries, vector and lexical indices, graph',
        'question': 'Question\nand scope',
        'lane': 'Select workflow\nPinned / all-library',
        'candidate': 'Gather candidates\nCatalogue / search',
        'judge': 'Optional Laya\nScore segments',
        'answer': 'Evidence + sources\nAgent synthesises',
        'notfound': 'Completed search\nScoped not-found',
        'failure': 'Execution failure',
        'query_note': 'A threshold score is not proof of support; failures are reported separately.',
    },
}
for name, changes in replacements.items():
    path = root / name
    tree = ET.parse(path)
    for cell in tree.iter('mxCell'):
        style = cell.get('style', '')
        if cell.get('value'):
            style = re.sub(r'fontSize=(1[3-9]|20);', 'fontSize=21;', style)
            cell.set('style', style)
        if cell.get('id') in changes:
            cell.set('value', changes[cell.get('id')])
    tree.write(path, encoding='utf-8', xml_declaration=True)
    print(path)
