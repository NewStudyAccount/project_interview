import sqlite3
import json
import sys

DB_PATH = r"C:\Users\AI\.local\share\mimocode\mimocode.db"

def query_db(sql, params=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if params:
        cursor.execute(sql, params)
    else:
        cursor.execute(sql)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def get_session_parts(sid):
    """Get all parts for a session with full data"""
    return query_db("""
        SELECT p.id, p.message_id, p.time_created, 
               json_extract(p.data, '$.type') as part_type,
               json_extract(p.data, '$.tool') as tool,
               p.data as full_data
        FROM part p
        WHERE p.session_id = ?
        ORDER BY p.time_created
    """, (sid,))

def get_message_content(sid):
    """Get all messages with content for a session"""
    return query_db("""
        SELECT m.id, m.agent_id, json_extract(m.data, '$.role') as role,
               json_extract(m.data, '$.content') as content,
               m.data as full_data
        FROM message m
        WHERE m.session_id = ?
        ORDER BY m.time_created
    """, (sid,))

if __name__ == "__main__":
    action = sys.argv[1]
    
    if action == "session_content":
        sid = sys.argv[2]
        messages = get_message_content(sid)
        for m in messages:
            print(f"=== Message {m['id']} (role={m['role']}, agent={m['agent_id']}) ===")
            if m['content']:
                content_str = str(m['content'])
                print(f"Content: {content_str[:500]}")
            print()
    
    elif action == "session_parts":
        sid = sys.argv[2]
        parts = get_session_parts(sid)
        for p in parts:
            data = p['full_data']
            # Try to parse and get key fields
            try:
                d = json.loads(data) if isinstance(data, str) else data
                ptype = d.get('type', 'unknown')
                if ptype == 'tool':
                    tool_name = d.get('tool', 'unknown')
                    state = d.get('state', {})
                    inp = state.get('input', {})
                    out = state.get('output', {})
                    print(f"  Part {p['id']}: TOOL={tool_name}")
                    if inp:
                        print(f"    Input: {json.dumps(inp, ensure_ascii=False)[:300]}")
                    if out:
                        out_str = json.dumps(out, ensure_ascii=False)
                        print(f"    Output: {out_str[:400]}")
                elif ptype == 'text':
                    text = d.get('text', '')
                    print(f"  Part {p['id']}: TEXT")
                    print(f"    {text[:500]}")
                elif ptype == 'step-start':
                    print(f"  Part {p['id']}: STEP-START")
                elif ptype == 'step-finish':
                    print(f"  Part {p['id']}: STEP-FINISH tokens={d.get('tokens', '')}")
                else:
                    print(f"  Part {p['id']}: TYPE={ptype}")
                    print(f"    {json.dumps(d, ensure_ascii=False)[:300]}")
            except:
                print(f"  Part {p['id']}: raw data")
                print(f"    {str(data)[:300]}")
            print()
    
    elif action == "search_user":
        keyword = sys.argv[2]
        results = query_db(f"""
            SELECT m.session_id, json_extract(m.data, '$.content') as content,
                   json_extract(m.data, '$.time.created') as time
            FROM message m
            WHERE json_extract(m.data, '$.role') = 'user'
              AND m.data LIKE '%{keyword}%'
            ORDER BY json_extract(m.data, '$.time.created') DESC
            LIMIT 30
        """)
        for r in results:
            print(f"  session={r['session_id']}")
            content = str(r['content']) if r['content'] else '(no content)'
            print(f"    content: {content[:500]}")
            print()
    
    elif action == "search_text_parts":
        keyword = sys.argv[2]
        results = query_db(f"""
            SELECT p.session_id, p.message_id, json_extract(p.data, '$.text') as text
            FROM part p
            WHERE json_extract(p.data, '$.type') = 'text'
              AND p.data LIKE '%{keyword}%'
            ORDER BY p.time_created DESC
            LIMIT 20
        """)
        for r in results:
            print(f"  session={r['session_id']} msg={r['message_id']}")
            text = str(r['text']) if r['text'] else '(no text)'
            print(f"    text: {text[:500]}")
            print()
    
    elif action == "tool_calls":
        sid = sys.argv[2]
        tool_filter = sys.argv[3] if len(sys.argv) > 3 else None
        if tool_filter:
            results = query_db(f"""
                SELECT p.session_id, json_extract(p.data, '$.tool') as tool,
                       json_extract(p.data, '$.state.input') as input_data,
                       json_extract(p.data, '$.state.output') as output_data
                FROM part p
                WHERE p.session_id = ?
                  AND json_extract(p.data, '$.type') = 'tool'
                  AND json_extract(p.data, '$.tool') = '{tool_filter}'
                ORDER BY p.time_created
            """, (sid,))
        else:
            results = query_db(f"""
                SELECT p.session_id, json_extract(p.data, '$.tool') as tool,
                       json_extract(p.data, '$.state.input') as input_data,
                       json_extract(p.data, '$.state.output') as output_data
                FROM part p
                WHERE p.session_id = ?
                  AND json_extract(p.data, '$.type') = 'tool'
                ORDER BY p.time_created
            """, (sid,))
        for r in results:
            print(f"  tool={r['tool']}")
            inp = str(r['input_data']) if r['input_data'] else ''
            out = str(r['output_data']) if r['output_data'] else ''
            print(f"    input: {inp[:400]}")
            print(f"    output: {out[:400]}")
            print()
