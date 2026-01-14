from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import json
import os
import anthropic

load_dotenv()
from database import get_db, RACMDatabase

app = Flask(__name__)

# Claude API key - set via environment variable
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# Initialize database
db = get_db()

# Seed initial data if database is empty
def seed_initial_data():
    """Add sample data if database is empty."""
    if not db.get_all_risks():
        db.create_risk('R001', 'Unauthorized system access', 'C001', 'IT Security', '', '', '', '', 'Not Complete', 0, '', 0, 0)
        db.create_risk('R002', 'Data integrity issues', 'C002', 'Data Team', '', '', '', '', 'Effective', 0, '', 0, 0)
        db.create_risk('R003', 'Segregation of duties', 'C003', 'HR/IT', '', '', '', '', 'Not Effective', 1, 'John', 1, 0)

    if not db.get_all_tasks():
        db.create_task('Define audit scope', 'Identify key processes and risks', 'medium', '', 'planning')
        db.create_task('Request documentation', 'PBC list to client', 'medium', '', 'planning')
        db.create_task('Control walkthroughs', 'Document process flows', 'medium', '', 'fieldwork')

seed_initial_data()

# Data version for frontend refresh detection
data_version = 0

@app.route('/')
def index():
    return render_template('index.html')

# ==================== RACM (Spreadsheet) API ====================

@app.route('/api/data', methods=['GET'])
def get_data():
    """Get RACM data in spreadsheet format."""
    return jsonify(db.get_as_spreadsheet())

@app.route('/api/data', methods=['POST'])
def save_data():
    """Save RACM data from spreadsheet format."""
    global data_version
    db.save_from_spreadsheet(request.json)
    data_version += 1
    return jsonify({'status': 'saved'})

# ==================== Risks API (for direct access) ====================

@app.route('/api/risks', methods=['GET'])
def get_risks():
    """Get all risks as JSON."""
    return jsonify(db.get_all_risks())

@app.route('/api/risks/<risk_id>', methods=['GET'])
def get_risk(risk_id):
    """Get a single risk."""
    risk = db.get_risk(risk_id)
    return jsonify(risk) if risk else ('Not found', 404)

@app.route('/api/risks', methods=['POST'])
def create_risk():
    """Create a new risk."""
    global data_version
    data = request.json
    new_id = db.create_risk(
        risk_id=data.get('risk_id'),
        risk_description=data.get('risk_description', ''),
        control_description=data.get('control_description', ''),
        control_owner=data.get('control_owner', ''),
        frequency=data.get('frequency', ''),
        status=data.get('status', 'Not Tested')
    )
    data_version += 1
    return jsonify({'status': 'created', 'id': new_id})

@app.route('/api/risks/<risk_id>', methods=['PUT'])
def update_risk(risk_id):
    """Update a risk."""
    global data_version
    db.update_risk(risk_id, **request.json)
    data_version += 1
    return jsonify({'status': 'updated'})

@app.route('/api/risks/<risk_id>', methods=['DELETE'])
def delete_risk(risk_id):
    """Delete a risk."""
    global data_version
    if db.delete_risk(risk_id):
        data_version += 1
        return jsonify({'status': 'deleted'})
    return ('Not found', 404)

# ==================== Flowchart API ====================

@app.route('/flowchart')
@app.route('/flowchart/<flowchart_id>')
def flowchart(flowchart_id=None):
    return render_template('flowchart.html', flowchart_id=flowchart_id)

@app.route('/api/flowchart/<flowchart_id>', methods=['GET'])
def get_flowchart(flowchart_id):
    """Get a flowchart by name."""
    fc = db.get_flowchart(flowchart_id)
    return jsonify(fc['data'] if fc else None)

@app.route('/api/flowchart/<flowchart_id>', methods=['POST'])
def save_flowchart(flowchart_id):
    """Save a flowchart."""
    global data_version
    db.save_flowchart(flowchart_id, request.json)
    data_version += 1
    return jsonify({'status': 'saved'})

@app.route('/api/flowcharts', methods=['GET'])
def list_flowcharts():
    """List all flowchart names."""
    flowcharts = db.get_all_flowcharts()
    return jsonify([f['name'] for f in flowcharts])

# ==================== Test Documents API ====================

@app.route('/api/test-document/<risk_code>/<doc_type>', methods=['GET'])
def get_test_document(risk_code, doc_type):
    """Get a test document by risk code and type (de_testing or oe_testing)."""
    if doc_type not in ('de_testing', 'oe_testing'):
        return jsonify({'error': 'Invalid document type'}), 400
    doc = db.get_test_document_by_risk_code(risk_code, doc_type)
    if doc:
        return jsonify({'content': doc['content'], 'id': doc['id']})
    return jsonify({'content': '', 'id': None})

@app.route('/api/test-document/<risk_code>/<doc_type>', methods=['POST'])
def save_test_document(risk_code, doc_type):
    """Save a test document."""
    global data_version
    if doc_type not in ('de_testing', 'oe_testing'):
        return jsonify({'error': 'Invalid document type'}), 400
    data = request.json
    content = data.get('content', '')
    doc_id = db.save_test_document_by_risk_code(risk_code, doc_type, content)
    if doc_id is None:
        return jsonify({'error': 'Risk not found'}), 404
    data_version += 1
    return jsonify({'status': 'saved', 'id': doc_id})

@app.route('/api/test-document/<risk_code>/<doc_type>/exists', methods=['GET'])
def test_document_exists(risk_code, doc_type):
    """Check if a test document exists."""
    if doc_type not in ('de_testing', 'oe_testing'):
        return jsonify({'error': 'Invalid document type'}), 400
    exists = db.has_test_document(risk_code, doc_type)
    return jsonify({'exists': exists})

# ==================== Kanban API ====================

@app.route('/kanban')
@app.route('/kanban/<board_id>')
def kanban(board_id='default'):
    return render_template('kanban.html', board_id=board_id)

@app.route('/api/kanban/<board_id>', methods=['GET'])
def get_kanban(board_id):
    """Get kanban board in legacy format."""
    kanban_format = db.get_kanban_format()
    return jsonify(kanban_format['boards'].get(board_id))

@app.route('/api/kanban/<board_id>', methods=['POST'])
def save_kanban(board_id):
    """Save kanban board from legacy format."""
    global data_version
    data = request.json

    # Clear existing tasks and recreate from the board data
    # This is a simple approach - in production you'd want smarter sync
    for col in data.get('columns', []):
        for item in col.get('items', []):
            task = db.get_task(int(item['id'])) if item['id'].isdigit() else None
            if task:
                db.update_task(int(item['id']),
                              title=item.get('title', ''),
                              description=item.get('description', ''),
                              priority=item.get('priority', 'medium'),
                              assignee=item.get('assignee', ''),
                              column_id=col['id'])

    data_version += 1
    return jsonify({'status': 'saved'})

@app.route('/api/kanban/<board_id>/task', methods=['POST'])
def create_kanban_task(board_id):
    """Create a new task on the kanban board."""
    global data_version
    data = request.json

    task_id = db.create_task(
        title=data.get('title', 'New Task'),
        description=data.get('description', ''),
        priority=data.get('priority', 'medium'),
        assignee=data.get('assignee', ''),
        column_id=data.get('column', 'planning'),
        risk_id=data.get('riskId', None)
    )

    data_version += 1
    return jsonify({'status': 'created', 'taskId': str(task_id)})

@app.route('/api/kanban/<board_id>/task/<task_id>', methods=['GET'])
def get_kanban_task(board_id, task_id):
    """Get a specific task."""
    task = db.get_task(int(task_id))
    if task:
        return jsonify({
            'id': str(task['id']),
            'title': task['title'],
            'description': task['description'],
            'priority': task['priority'],
            'assignee': task['assignee'],
            'column': task['column_id'],
            'riskId': task['linked_risk_id'] or ''
        })
    return jsonify(None)

@app.route('/api/kanban/<board_id>/task/<task_id>', methods=['PUT'])
def update_kanban_task(board_id, task_id):
    """Update a specific task."""
    global data_version
    data = request.json
    db.update_task(int(task_id), **{
        'title': data.get('title'),
        'description': data.get('description'),
        'priority': data.get('priority'),
        'assignee': data.get('assignee'),
        'column_id': data.get('column')
    })
    data_version += 1
    return jsonify({'status': 'updated'})

# ==================== Tasks API (direct access) ====================

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks."""
    return jsonify(db.get_all_tasks())

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """Get a single task."""
    task = db.get_task(task_id)
    return jsonify(task) if task else ('Not found', 404)

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create a new task."""
    global data_version
    data = request.json
    task_id = db.create_task(
        title=data.get('title'),
        description=data.get('description', ''),
        priority=data.get('priority', 'medium'),
        assignee=data.get('assignee', ''),
        column_id=data.get('column_id', 'planning'),
        risk_id=data.get('risk_id')
    )
    data_version += 1
    return jsonify({'status': 'created', 'id': task_id})

# ==================== AI Query API ====================

@app.route('/api/query', methods=['POST'])
def query_database():
    """Execute a read-only SQL query (for AI integration)."""
    data = request.json
    sql = data.get('sql', '')
    try:
        results = db.execute_query(sql)
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/schema', methods=['GET'])
def get_schema():
    """Get database schema for AI context."""
    return jsonify({'schema': db.get_schema()})

@app.route('/api/context', methods=['GET'])
def get_context():
    """Get full database context for AI."""
    return jsonify(db.get_full_context())

# ==================== Export/Import ====================

@app.route('/api/export', methods=['GET'])
def export_data():
    """Export all data as JSON."""
    return jsonify(db.export_all())

@app.route('/api/import', methods=['POST'])
def import_data():
    """Import data from JSON."""
    global data_version
    data = request.json
    clear = request.args.get('clear', 'false').lower() == 'true'
    db.import_all(data, clear_existing=clear)
    data_version += 1
    return jsonify({'status': 'imported'})

# ==================== Chat API ====================

chat_history = []

@app.route('/api/chat/status', methods=['GET'])
def chat_status():
    """Check if API key is configured."""
    return jsonify({'configured': bool(ANTHROPIC_API_KEY)})

@app.route('/api/chat', methods=['POST'])
def chat():
    global data_version
    data = request.json
    user_message = data.get('message', '')
    api_key = ANTHROPIC_API_KEY

    if not api_key:
        return jsonify({'error': 'No API key provided. Set ANTHROPIC_API_KEY environment variable.'})

    # Get full context from database
    context = db.get_full_context()

    # Build system prompt with schema info
    system_prompt = f"""You are an AI audit assistant helping internal auditors. You can both analyze data AND take actions.

## Database Schema
{context['schema']}

## Current Audit Data Summary:
- Total Risks: {context['risk_summary']['total']}
- Status Breakdown: {json.dumps(context['risk_summary']['by_status'])}
- Total Tasks: {context['task_summary']['total']}
- Tasks by Stage: {json.dumps(context['task_summary']['by_column'])}
- Flowcharts: {context['flowchart_count']}

## Current RACM Data:
{json.dumps(context['risks'], indent=2)}

## Current Tasks:
{json.dumps(context['tasks'], indent=2)}

## Your Capabilities:
1. Answer questions about the audit data
2. Use tools to ADD new rows to RACM, CREATE Kanban tasks, or UPDATE data
3. Execute SQL queries to analyze data
4. When asked to add/create something, USE THE APPROPRIATE TOOL

Be concise and professional."""

    # Define tools
    tools = [
        {
            "name": "add_racm_row",
            "description": "Add a new row to the Risk and Control Matrix (RACM).",
            "input_schema": {
                "type": "object",
                "properties": {
                    "risk_id": {"type": "string", "description": "Risk ID (e.g., R004)"},
                    "risk_description": {"type": "string", "description": "Description of the risk"},
                    "control_description": {"type": "string", "description": "Description of the control"},
                    "control_owner": {"type": "string", "description": "Who owns this control"},
                    "frequency": {"type": "string", "description": "How often (Daily, Weekly, Monthly, Quarterly)"},
                    "status": {"type": "string", "description": "Status (Effective, Needs Improvement, Ineffective, Not Tested)"}
                },
                "required": ["risk_id", "risk_description", "control_description"]
            }
        },
        {
            "name": "create_kanban_task",
            "description": "Create a new task on the Kanban board.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Task description"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "assignee": {"type": "string", "description": "Who is assigned"},
                    "column": {"type": "string", "enum": ["planning", "fieldwork", "testing", "review", "complete"]},
                    "risk_id": {"type": "string", "description": "Link to RACM Risk ID (e.g., 'R001')"}
                },
                "required": ["title"]
            }
        },
        {
            "name": "update_racm_status",
            "description": "Update the status of an existing RACM row.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "risk_id": {"type": "string", "description": "Risk ID to update (e.g., R001)"},
                    "new_status": {"type": "string", "enum": ["Effective", "Needs Improvement", "Ineffective", "Not Tested"]}
                },
                "required": ["risk_id", "new_status"]
            }
        },
        {
            "name": "execute_sql",
            "description": "Execute a read-only SQL query to analyze audit data. Use for complex queries.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SELECT query to execute"}
                },
                "required": ["sql"]
            }
        },
        {
            "name": "get_audit_summary",
            "description": "Get a summary of current audit status.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "create_flowchart",
            "description": "Create a new process flowchart.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Flowchart name"},
                    "risk_id": {"type": "string", "description": "Link to RACM Risk ID"},
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": ["start", "process", "decision", "control", "end"]},
                                "label": {"type": "string"},
                                "description": {"type": "string"}
                            },
                            "required": ["type", "label"]
                        }
                    }
                },
                "required": ["name", "steps"]
            }
        }
    ]

    try:
        client = anthropic.Anthropic(api_key=api_key)
        chat_history.append({"role": "user", "content": user_message})
        messages = chat_history[-10:]

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

        final_response = ""
        tool_results = []

        while response.stop_reason == "tool_use":
            for content in response.content:
                if content.type == "tool_use":
                    result = execute_tool(content.name, content.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content.id,
                        "content": result
                    })
                elif content.type == "text":
                    final_response += content.text

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=system_prompt,
                tools=tools,
                messages=messages
            )
            tool_results = []

        for content in response.content:
            if hasattr(content, 'text'):
                final_response += content.text

        chat_history.append({"role": "assistant", "content": final_response})
        return jsonify({'response': final_response, 'data_version': data_version})

    except anthropic.AuthenticationError:
        return jsonify({'error': 'Invalid API key'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})


def execute_tool(tool_name, tool_input):
    """Execute a tool and return the result."""
    global data_version

    if tool_name == "add_racm_row":
        db.create_risk(
            risk_id=tool_input.get('risk_id', ''),
            risk_description=tool_input.get('risk_description', ''),
            control_description=tool_input.get('control_description', ''),
            control_owner=tool_input.get('control_owner', ''),
            frequency=tool_input.get('frequency', ''),
            status=tool_input.get('status', 'Not Tested')
        )
        data_version += 1
        return f"Successfully added RACM row: {tool_input.get('risk_id')} - {tool_input.get('risk_description')}"

    elif tool_name == "create_kanban_task":
        risk_id = tool_input.get('risk_id', '')
        task_id = db.create_task(
            title=tool_input.get('title', 'New Task'),
            description=tool_input.get('description', ''),
            priority=tool_input.get('priority', 'medium'),
            assignee=tool_input.get('assignee', ''),
            column_id=tool_input.get('column', 'planning'),
            risk_id=risk_id if risk_id else None
        )
        data_version += 1
        linked_msg = f" Linked to RACM row {risk_id}." if risk_id else ""
        return f"Successfully created task '{tool_input.get('title')}' (ID: {task_id}).{linked_msg}"

    elif tool_name == "update_racm_status":
        risk_id = tool_input.get('risk_id', '').upper()
        new_status = tool_input.get('new_status', '')
        if db.update_risk(risk_id, status=new_status):
            data_version += 1
            return f"Successfully updated {risk_id} status to '{new_status}'"
        return f"Risk ID '{risk_id}' not found"

    elif tool_name == "execute_sql":
        sql = tool_input.get('sql', '')
        try:
            results = db.execute_query(sql)
            return json.dumps(results, indent=2)
        except Exception as e:
            return f"Query error: {str(e)}"

    elif tool_name == "get_audit_summary":
        summary = {
            'risks': db.get_risk_summary(),
            'tasks': db.get_task_summary(),
            'flowcharts': len(db.get_all_flowcharts())
        }
        return json.dumps(summary, indent=2)

    elif tool_name == "create_flowchart":
        name = tool_input.get('name', 'new-flowchart').lower().replace(' ', '-')
        steps = tool_input.get('steps', [])
        risk_id = tool_input.get('risk_id', '')

        # Build Drawflow data structure
        drawflow_data = {"drawflow": {"Home": {"data": {}}}}
        nodes = drawflow_data["drawflow"]["Home"]["data"]

        node_config = {
            'start': {'inputs': 0, 'outputs': 1},
            'process': {'inputs': 1, 'outputs': 1},
            'decision': {'inputs': 1, 'outputs': 2},
            'control': {'inputs': 1, 'outputs': 1},
            'end': {'inputs': 1, 'outputs': 0},
        }

        y_pos = 50
        prev_node_id = None

        for i, step in enumerate(steps):
            node_id = str(i + 1)
            node_type = step.get('type', 'process')
            label = step.get('label', 'Step')
            description = step.get('description', '')

            config = node_config.get(node_type, {'inputs': 1, 'outputs': 1})

            inputs = {}
            if config['inputs'] > 0:
                inputs["input_1"] = {"connections": []}
                if prev_node_id:
                    inputs["input_1"]["connections"].append({
                        "node": prev_node_id,
                        "input": "output_1"
                    })

            outputs = {}
            for j in range(config['outputs']):
                outputs[f"output_{j+1}"] = {"connections": []}

            nodes[node_id] = {
                "id": int(node_id),
                "name": node_type,
                "data": {"name": label, "description": description},
                "class": node_type,
                "html": f'<div class="node-header"><input type="text" class="header-input" value="{label}" df-name></div><div class="node-body"><textarea class="node-textarea" placeholder="Description..." df-description>{description}</textarea></div>',
                "typenode": False,
                "inputs": inputs,
                "outputs": outputs,
                "pos_x": 150,
                "pos_y": y_pos
            }

            if prev_node_id and prev_node_id in nodes:
                nodes[prev_node_id]["outputs"]["output_1"]["connections"].append({
                    "node": node_id,
                    "output": "input_1"
                })

            prev_node_id = node_id
            y_pos += 150

        db.save_flowchart(name, drawflow_data, risk_id if risk_id else None)
        data_version += 1

        linked_msg = f" Linked to RACM row {risk_id}." if risk_id else ""
        return f"Successfully created flowchart '{name}' with {len(steps)} nodes.{linked_msg} View at: /flowchart/{name}"

    return "Unknown tool"


@app.route('/api/chat/clear', methods=['POST'])
def clear_chat():
    global chat_history
    chat_history = []
    return jsonify({'status': 'cleared'})


if __name__ == '__main__':
    app.run(debug=True, port=8002)
