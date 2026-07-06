#!/usr/bin/env python3
"""Parse KSP .sfs save files into structured JSON.

Usage:
    python scripts/save-parser.py <path-to-persistent.sfs>
    python scripts/save-parser.py --minify <path>
    python scripts/save-parser.py --pretty <path>

Outputs JSON to stdout. Exits with non-zero on error.
Designed for KSP 1.12.5 .sfs format with nested { } blocks.
"""

import json
import re
import sys
import argparse

# ---------------------------------------------------------------------------
# SFS tokeniser / parser
# ---------------------------------------------------------------------------

def tokenise(text: str):
    """Yield (kind, value) tokens from raw .sfs text."""
    # Strip BOM if present
    if text.startswith('\ufeff'):
        text = text[1:]
    # Normalise line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = text.split('\n')
    # Lookahead: track if previous line was a bare identifier (block name)
    prev_bare_id = None
    for lineno, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line:
            continue
        # Standalone }
        if line == '}':
            prev_bare_id = None
            yield ('close', lineno)
            continue
        # Key = value  (value may contain = signs e.g. in paths, so only split on first =)
        m = re.match(r'^([^=]+?)\s*=\s*(.*)$', line)
        if m:
            prev_bare_id = None
            key = m.group(1).strip()
            value = m.group(2).strip()
            yield ('kv', key, value, lineno)
            continue
        # Block open: KEY {
        m = re.match(r'^(\S+)\s*\{\s*$', line)
        if m:
            prev_bare_id = None
            yield ('open', m.group(1), lineno)
            continue
        # Standalone {
        if line == '{':
            # If previous line was a bare identifier, use it as block key
            if prev_bare_id is not None:
                yield ('open', prev_bare_id, lineno)
                prev_bare_id = None
            else:
                yield ('open', None, lineno)
            continue
        # Bare identifier (block name on its own line before {)
        if re.match(r'^[A-Za-z_][\w.]*$', line):
            prev_bare_id = line
            continue
        # Any other line — reset lookahead
        prev_bare_id = None

def parse_sfs(text: str):
    """Parse .sfs text into nested dicts/lists.

    Repeated keys at the same level become a list.
    """
    tokens = list(tokenise(text))
    pos = [0]

    def peek():
        if pos[0] < len(tokens):
            return tokens[pos[0]]
        return None

    def advance():
        tok = tokens[pos[0]]
        pos[0] += 1
        return tok

    def parse_node():
        """Parse a single node (block or kv)."""
        tok = peek()
        if tok is None:
            return None
        kind = tok[0]
        if kind in ('open',):
            # Block
            advance()  # consume open
            key = tok[1]
            children = parse_children()
            # Consume close
            close = advance() if peek() and peek()[0] == 'close' else None
            return ('block', key, children)
        elif kind == 'kv':
            advance()
            return ('kv', tok[1], tok[2], tok[3])
        elif kind == 'close':
            return None
        return None

    def parse_children():
        children = []
        while pos[0] < len(tokens):
            if peek()[0] == 'close':
                break
            node = parse_node()
            if node is None:
                break
            children.append(node)
        return children

    root_children = parse_children()
    # Build dict: fold repeated sibling keys into lists
    result = collapse(root_children)
    return result

def collapse(nodes):
    """Convert list of (type, ...) tuples into dict, collapsing repeated keys."""
    d = {}
    for node in nodes:
        kind = node[0]
        if kind == 'kv':
            key = node[1]
            val = coerce_value(node[2])
            if key in d:
                existing = d[key]
                if not isinstance(existing, list):
                    d[key] = [existing]
                d[key].append(val)
            else:
                d[key] = val
        elif kind == 'block':
            key = node[1]
            children = node[2]
            sub = collapse(children)
            if key in d:
                existing = d[key]
                if not isinstance(existing, list):
                    d[key] = [existing]
                d[key].append(sub)
            else:
                d[key] = sub
        # else: ignore
    return d

def coerce_value(raw: str):
    """Convert .sfs string values to native types."""
    v = raw.strip()
    if v == '':
        return ''
    # Booleans
    if v == 'True':
        return True
    if v == 'False':
        return False
    # Numbers
    try:
        if '.' in v or 'e' in v.lower():
            return float(v)
        return int(v)
    except (ValueError, TypeError):
        pass
    # Comma-separated numbers (common in KSP saves for vector values)
    if ',' in v:
        parts = [p.strip() for p in v.split(',')]
        # Coerce each part
        coerced = []
        for p in parts:
            try:
                if '.' in p or 'e' in p.lower():
                    coerced.append(float(p))
                else:
                    coerced.append(int(p))
            except (ValueError, TypeError):
                coerced.append(p)
        # If all parts were numeric, return list; else keep string
        if all(isinstance(c, (int, float)) for c in coerced):
            return coerced
    return v

# ---------------------------------------------------------------------------
# Career-specific extraction
# ---------------------------------------------------------------------------

def extract_career(data: dict) -> dict:
    """Extract high-level career pulse from parsed save.

    In KSP 1.12.5 career saves, data lives in SCENARIO blocks:
      - SCENARIO Funding        -> funds
      - SCENARIO Reputation     -> rep
      - SCENARIO ResearchAndDevelopment -> sci, Tech[]
      - SCENARIO ContractSystem -> CONTRACTS
      - FLIGHTSTATE             -> VESSEL[]
    """
    game = data.get('GAME', data)

    # --- collect SCENARIO blocks by name ---
    scenarios = {}
    raw_scenarios = game.get('SCENARIO', [])
    if isinstance(raw_scenarios, dict):
        raw_scenarios = [raw_scenarios]
    for sc in raw_scenarios:
        if isinstance(sc, dict):
            name = sc.get('name', '')
            scenarios[name] = sc

    # --- meta ---
    meta = {
        'version': game.get('version', ''),
        'title': game.get('Title', ''),
        'mode': game.get('Mode', ''),
        'scene': game.get('scene', ''),
    }

    # --- currency ---
    funding = scenarios.get('Funding', {})
    funds = funding.get('funds', 0.0)

    reputation = scenarios.get('Reputation', {})
    rep = reputation.get('rep', 0.0)

    rd_scenario = scenarios.get('ResearchAndDevelopment', {})
    science = rd_scenario.get('sci', 0.0)

    # --- tech nodes ---
    tech_nodes = []
    tech_raw = rd_scenario.get('Tech', [])
    if isinstance(tech_raw, dict):
        tech_raw = [tech_raw]
    for tech in tech_raw:
        if isinstance(tech, dict):
            tid = tech.get('id', '')
            if tid:
                parts = tech.get('part', [])
                if isinstance(parts, str):
                    parts = [parts]
                tech_nodes.append({
                    'id': tid,
                    'state': tech.get('state', ''),
                    'cost': tech.get('cost', 0),
                    'parts': parts,
                })

    # --- contracts ---
    cs = scenarios.get('ContractSystem', {})
    contracts_data = cs.get('CONTRACTS', {})
    if isinstance(contracts_data, list):
        contracts_data = contracts_data[0] if contracts_data else {}

    contracts_raw = contracts_data.get('CONTRACT', [])
    if isinstance(contracts_raw, dict):
        contracts_raw = [contracts_raw]

    state_map = {
        'Offered': 'offered',
        'Active': 'active',
        'Completed': 'completed',
        'Failed': 'failed',
        'Declined': 'declined',
        'Withdrawn': 'withdrawn',
        'Expired': 'expired',
        'DeadlineExpired': 'expired',
    }

    contracts = []
    for c in contracts_raw:
        if not isinstance(c, dict):
            continue
        state = c.get('state', '')
        mapped = state_map.get(state, state.lower() if state else 'unknown')
        contract = {
            'guid': c.get('guid', ''),
            'type': str(c.get('type', '')),
            'prestige': c.get('prestige', 0),
            'state': mapped,
            'agent': c.get('agent', ''),
            'seed': c.get('seed', 0),
        }
        # Parse values field (comma-separated floats: advance,reward_f,reward_r,penalty_f,penalty_r,...)
        values = c.get('values', '')
        if isinstance(values, str) and values:
            parts = values.split(',')
            if len(parts) >= 5:
                contract['advance_fee'] = _safe_float(parts[0])
                contract['reward_funds'] = _safe_float(parts[1])
                contract['reward_rep'] = _safe_float(parts[2])
                contract['penalty_funds'] = _safe_float(parts[3])
                contract['penalty_rep'] = _safe_float(parts[4])
        elif isinstance(values, list) and len(values) >= 5:
            contract['advance_fee'] = _safe_float(values[0])
            contract['reward_funds'] = _safe_float(values[1])
            contract['reward_rep'] = _safe_float(values[2])
            contract['penalty_funds'] = _safe_float(values[3])
            contract['penalty_rep'] = _safe_float(values[4])
        contracts.append(contract)

    active = [c for c in contracts if c['state'] == 'active']
    offered = [c for c in contracts if c['state'] == 'offered']
    completed = [c for c in contracts if c['state'] == 'completed']

    # --- vessels ---
    flight_state = game.get('FLIGHTSTATE', {})
    if isinstance(flight_state, list):
        flight_state = flight_state[0] if flight_state else {}

    vessels_raw = flight_state.get('VESSEL', [])
    if isinstance(vessels_raw, dict):
        vessels_raw = [vessels_raw]

    vessels = []
    for v in vessels_raw:
        if not isinstance(v, dict):
            continue
        orbit_data = v.get('ORBIT', None)
        orbit = None
        if orbit_data:
            if isinstance(orbit_data, list):
                orbit_data = orbit_data[0] if orbit_data else {}
            if isinstance(orbit_data, dict):
                orbit = {
                    'body': orbit_data.get('REF', ''),
                    'sma': orbit_data.get('SMA', 0),
                    'ecc': orbit_data.get('ECC', 0),
                    'inc': orbit_data.get('INC', 0),
                }
        # crew count: may be '\nautoLOC_...' string, count only if int
        crew_count = 0
        cval = v.get('crew', 0)
        if isinstance(cval, int):
            crew_count = cval
        elif isinstance(cval, list):
            crew_count = len(cval)
        vessels.append({
            'name': v.get('name', ''),
            'type': v.get('type', ''),
            'situation': str(v.get('sit', '')),
            'landed': v.get('landed', False),
            'splashed': v.get('splashed', False),
            'landed_at': v.get('landedAt', ''),
            'orbit': orbit,
            'crew_count': crew_count,
            'persistent_id': v.get('persistentId', 0),
        })

    return {
        'meta': meta,
        'currency': {
            'funds': funds,
            'science': science,
            'reputation': rep,
        },
        'tech_nodes': tech_nodes,
        'contracts': {
            'total': len(contracts),
            'active': len(active),
            'offered': len(offered),
            'completed': len(completed),
            'active_list': active,
            'offered_list': offered,
        },
        'vessels': {
            'total': len(vessels),
            'list': vessels,
        },
    }


def _safe_float(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Parse KSP .sfs save files into structured JSON'
    )
    parser.add_argument('path', help='Path to persistent.sfs file')
    parser.add_argument('--minify', action='store_true',
                        help='Output compact JSON (no indentation)')
    parser.add_argument('--pretty', action='store_true',
                        help='Output pretty-printed JSON (default)')
    parser.add_argument('--raw', action='store_true',
                        help='Output full raw parse tree instead of career summary')
    args = parser.parse_args()

    try:
        with open(args.path, 'r', encoding='utf-8') as f:
            text = f.read()
    except FileNotFoundError:
        print(json.dumps({"error": f"File not found: {args.path}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": f"Failed to read file: {e}"}))
        sys.exit(1)

    try:
        parsed = parse_sfs(text)
    except Exception as e:
        print(json.dumps({"error": f"Parse error: {e}"}))
        sys.exit(1)

    if args.raw:
        output = parsed
    else:
        output = extract_career(parsed)

    indent = None if args.minify else 2
    json.dump(output, sys.stdout, indent=indent, default=str)
    sys.stdout.write('\n')


if __name__ == '__main__':
    main()
