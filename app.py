from flask import Flask, render_template, request, jsonify
import json
import os
import anthropic

app = Flask(__name__)

# Claude API key - set via environment variable or enter in UI
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

# In-memory storage (replace with database for production)
flowchart_data = {}  # Store flowcharts by ID
data_version = 0  # Increments on any data change for frontend refresh

spreadsheet_data = [
    ['Risk ID', 'Risk Description', 'Control Description', 'Control Owner', 'Frequency', 'Status', 'Flowchart', 'Task'],
    ['R001', 'Unauthorized system access', 'Quarterly access reviews', 'IT Security', 'Quarterly', 'Effective', '', ''],
    ['R002', 'Data integrity issues', 'Automated validation checks', 'Data Team', 'Daily', 'Effective', '', ''],
    ['R003', 'Segregation of duties', 'Role-based access controls', 'HR/IT', 'Ongoing', 'Needs Improvement', '', ''],
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify(spreadsheet_data)

@app.route('/api/data', methods=['POST'])
def save_data():
    global spreadsheet_data
    spreadsheet_data = request.json
    return jsonify({'status': 'saved'})

@app.route('/flowchart')
@app.route('/flowchart/<flowchart_id>')
def flowchart(flowchart_id=None):
    return render_template('flowchart.html', flowchart_id=flowchart_id)

@app.route('/api/flowchart/<flowchart_id>', methods=['GET'])
def get_flowchart(flowchart_id):
    return jsonify(flowchart_data.get(flowchart_id, None))

@app.route('/api/flowchart/<flowchart_id>', methods=['POST'])
def save_flowchart(flowchart_id):
    flowchart_data[flowchart_id] = request.json
    return jsonify({'status': 'saved'})

@app.route('/api/flowcharts', methods=['GET'])
def list_flowcharts():
    return jsonify(list(flowchart_data.keys()))

# Kanban board storage
kanban_data = {
    'boards': {
        'default': {
            'name': 'Audit Plan',
            'columns': [
                {
                    'id': 'planning',
                    'title': 'Planning',
                    'items': [
                        {'id': '1', 'title': 'Define audit scope', 'description': 'Identify key processes and risks'},
                        {'id': '2', 'title': 'Request documentation', 'description': 'PBC list to client'},
                    ]
                },
                {
                    'id': 'fieldwork',
                    'title': 'Fieldwork',
                    'items': [
                        {'id': '3', 'title': 'Control walkthroughs', 'description': 'Document process flows'},
                    ]
                },
                {
                    'id': 'testing',
                    'title': 'Testing',
                    'items': []
                },
                {
                    'id': 'review',
                    'title': 'Review',
                    'items': []
                },
                {
                    'id': 'complete',
                    'title': 'Complete',
                    'items': []
                }
            ]
        }
    }
}

@app.route('/kanban')
@app.route('/kanban/<board_id>')
def kanban(board_id='default'):
    return render_template('kanban.html', board_id=board_id)

@app.route('/api/kanban/<board_id>', methods=['GET'])
def get_kanban(board_id):
    return jsonify(kanban_data['boards'].get(board_id))

@app.route('/api/kanban/<board_id>', methods=['POST'])
def save_kanban(board_id):
    kanban_data['boards'][board_id] = request.json
    return jsonify({'status': 'saved'})

@app.route('/api/kanban/<board_id>/task', methods=['POST'])
def create_task(board_id):
    """Create a new task on the kanban board"""
    data = request.json

    # Ensure board exists
    if board_id not in kanban_data['boards']:
        kanban_data['boards'][board_id] = {
            'name': 'Audit Plan',
            'columns': [
                {'id': 'planning', 'title': 'Planning', 'items': []},
                {'id': 'fieldwork', 'title': 'Fieldwork', 'items': []},
                {'id': 'testing', 'title': 'Testing', 'items': []},
                {'id': 'review', 'title': 'Review', 'items': []},
                {'id': 'complete', 'title': 'Complete', 'items': []}
            ]
        }

    board = kanban_data['boards'][board_id]

    # Generate task ID
    import time
    task_id = f"task-{int(time.time() * 1000)}"

    # Create task
    task = {
        'id': task_id,
        'title': data.get('title', 'New Task'),
        'description': data.get('description', ''),
        'priority': data.get('priority', 'medium'),
        'assignee': data.get('assignee', ''),
        'dueDate': data.get('dueDate', ''),
        'riskId': data.get('riskId', ''),
        'racmRow': data.get('racmRow', None)
    }

    # Add to first column (Planning) by default
    target_column = data.get('column', 'planning')
    for col in board['columns']:
        if col['id'] == target_column:
            col['items'].append(task)
            break
    else:
        # If column not found, add to first column
        if board['columns']:
            board['columns'][0]['items'].append(task)

    return jsonify({'status': 'created', 'taskId': task_id})

@app.route('/api/kanban/<board_id>/task/<task_id>', methods=['GET'])
def get_task(board_id, task_id):
    """Get a specific task"""
    if board_id not in kanban_data['boards']:
        return jsonify(None)

    board = kanban_data['boards'][board_id]
    for col in board['columns']:
        for item in col['items']:
            if item['id'] == task_id:
                return jsonify({**item, 'column': col['id'], 'columnTitle': col['title']})

    return jsonify(None)

@app.route('/api/kanban/<board_id>/task/<task_id>', methods=['PUT'])
def update_task(board_id, task_id):
    """Update a specific task"""
    if board_id not in kanban_data['boards']:
        return jsonify({'status': 'error', 'message': 'Board not found'})

    data = request.json
    board = kanban_data['boards'][board_id]

    for col in board['columns']:
        for item in col['items']:
            if item['id'] == task_id:
                item['title'] = data.get('title', item['title'])
                item['description'] = data.get('description', item['description'])
                item['priority'] = data.get('priority', item['priority'])
                item['assignee'] = data.get('assignee', item['assignee'])
                item['dueDate'] = data.get('dueDate', item['dueDate'])
                return jsonify({'status': 'updated', 'column': col['id'], 'columnTitle': col['title']})

    return jsonify({'status': 'error', 'message': 'Task not found'})

# Chat endpoint
chat_history = []

@app.route('/api/chat/status', methods=['GET'])
def chat_status():
    """Check if API key is configured on server"""
    return jsonify({'configured': bool(ANTHROPIC_API_KEY)})

@app.route('/api/chat', methods=['POST'])
def chat():
    global ANTHROPIC_API_KEY, spreadsheet_data, kanban_data, flowchart_data
    data = request.json
    user_message = data.get('message', '')
    api_key = ANTHROPIC_API_KEY

    if not api_key:
        return jsonify({'error': 'No API key provided. Set ANTHROPIC_API_KEY environment variable.'})

    # Gather all audit data for context
    audit_context = gather_audit_context()

    # Build system prompt
    system_prompt = f"""You are an AI audit assistant helping internal auditors. You can both analyze data AND take actions.

## Current Audit Data:

### RACM (Risk and Control Matrix)
{json.dumps(audit_context['racm'], indent=2)}

### Kanban Board (Audit Planning)
{json.dumps(audit_context['kanban'], indent=2)}

### Process Flowcharts
{json.dumps(audit_context['flowcharts'], indent=2)}

## Your Capabilities:
1. Answer questions about the audit data
2. Use tools to ADD new rows to RACM, CREATE Kanban tasks, or UPDATE data
3. When asked to add/create something, USE THE APPROPRIATE TOOL - don't just describe what you would do

Be concise and professional. When you use a tool, confirm what was created."""

    # Define tools
    tools = [
        {
            "name": "add_racm_row",
            "description": "Add a new row to the Risk and Control Matrix (RACM). Use this when the user asks to add a new risk, control, or RACM entry.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "risk_id": {"type": "string", "description": "Risk ID (e.g., R004)"},
                    "risk_description": {"type": "string", "description": "Description of the risk"},
                    "control_description": {"type": "string", "description": "Description of the control"},
                    "control_owner": {"type": "string", "description": "Who owns this control"},
                    "frequency": {"type": "string", "description": "How often the control is performed (e.g., Daily, Weekly, Monthly, Quarterly)"},
                    "status": {"type": "string", "description": "Control status (Effective, Needs Improvement, Ineffective, Not Tested)"}
                },
                "required": ["risk_id", "risk_description", "control_description"]
            }
        },
        {
            "name": "create_kanban_task",
            "description": "Create a new task on the Kanban audit planning board. Use this when the user asks to add a task, todo, or work item. Always link to a RACM risk_id when creating tasks for specific controls.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Task title"},
                    "description": {"type": "string", "description": "Task description"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"], "description": "Task priority"},
                    "assignee": {"type": "string", "description": "Who is assigned to this task"},
                    "column": {"type": "string", "enum": ["planning", "fieldwork", "testing", "review", "complete"], "description": "Which column to add the task to"},
                    "risk_id": {"type": "string", "description": "Optional: Link this task to a RACM row by Risk ID (e.g., 'R001'). If provided, the RACM Task column will be updated."}
                },
                "required": ["title"]
            }
        },
        {
            "name": "update_racm_status",
            "description": "Update the status of an existing RACM row. Use when user wants to change a control's status.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "risk_id": {"type": "string", "description": "Risk ID to update (e.g., R001)"},
                    "new_status": {"type": "string", "enum": ["Effective", "Needs Improvement", "Ineffective", "Not Tested"], "description": "New status"}
                },
                "required": ["risk_id", "new_status"]
            }
        },
        {
            "name": "get_audit_summary",
            "description": "Get a summary of the current audit status including RACM stats, task progress, and flowchart count.",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "create_flowchart",
            "description": "Create a new process flowchart for audit walkthroughs. Use when user asks to create a flowchart or document a process flow. Always link to a RACM risk_id when creating flowcharts for specific controls.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Flowchart name/identifier (e.g., 'revenue-process', 'payroll-walkthrough')"},
                    "risk_id": {"type": "string", "description": "Optional: Link this flowchart to a RACM row by Risk ID (e.g., 'R001'). If provided, the RACM Flowchart column will be updated."},
                    "steps": {
                        "type": "array",
                        "description": "List of process steps to include in the flowchart",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": ["start", "process", "decision", "control", "end"], "description": "Type of node"},
                                "label": {"type": "string", "description": "Text label for the node"},
                                "description": {"type": "string", "description": "Additional description"}
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

        # Initial API call with tools
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

        # Process tool calls if any
        final_response = ""
        tool_results = []

        while response.stop_reason == "tool_use":
            # Process each tool use
            for content in response.content:
                if content.type == "tool_use":
                    tool_name = content.name
                    tool_input = content.input
                    tool_use_id = content.id

                    # Execute the tool
                    result = execute_tool(tool_name, tool_input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result
                    })
                elif content.type == "text":
                    final_response += content.text

            # Continue conversation with tool results
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

        # Get final text response
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
    """Execute a tool and return the result"""
    global spreadsheet_data, kanban_data, data_version

    if tool_name == "add_racm_row":
        # Add new row to RACM
        new_row = [
            tool_input.get('risk_id', ''),
            tool_input.get('risk_description', ''),
            tool_input.get('control_description', ''),
            tool_input.get('control_owner', ''),
            tool_input.get('frequency', ''),
            tool_input.get('status', 'Not Tested'),
            '',  # Flowchart
            ''   # Task
        ]
        spreadsheet_data.append(new_row)
        data_version += 1
        return f"Successfully added RACM row: {tool_input.get('risk_id')} - {tool_input.get('risk_description')}"

    elif tool_name == "create_kanban_task":
        # Create Kanban task
        import time
        task_id = f"task-{int(time.time() * 1000)}"
        risk_id = tool_input.get('risk_id', '')
        task = {
            'id': task_id,
            'title': tool_input.get('title', 'New Task'),
            'description': tool_input.get('description', ''),
            'priority': tool_input.get('priority', 'medium'),
            'assignee': tool_input.get('assignee', ''),
            'dueDate': '',
            'riskId': risk_id
        }

        board = kanban_data['boards'].get('default')
        if board:
            target_col = tool_input.get('column', 'planning')
            for col in board['columns']:
                if col['id'] == target_col:
                    col['items'].append(task)
                    data_version += 1

                    # Link to RACM row if risk_id provided
                    linked_msg = ""
                    if risk_id:
                        risk_id_upper = risk_id.upper()
                        for row in spreadsheet_data[1:]:  # Skip header
                            if row[0].upper() == risk_id_upper:
                                row[7] = task_id  # Set Task column (index 7)
                                linked_msg = f" Linked to RACM row {risk_id_upper}."
                                break

                    return f"Successfully created task '{task['title']}' in {col['title']} column.{linked_msg}"
        return "Failed to create task - board not found"

    elif tool_name == "update_racm_status":
        # Update RACM status
        risk_id = tool_input.get('risk_id', '').upper()
        new_status = tool_input.get('new_status', '')

        for row in spreadsheet_data[1:]:  # Skip header
            if row[0].upper() == risk_id:
                row[5] = new_status
                data_version += 1
                return f"Successfully updated {risk_id} status to '{new_status}'"
        return f"Risk ID '{risk_id}' not found in RACM"

    elif tool_name == "get_audit_summary":
        # Generate summary
        context = gather_audit_context()
        racm_rows = len(context['racm']['rows'])

        # Count statuses
        status_counts = {}
        for row in context['racm']['rows']:
            status = row.get('Status', 'Unknown')
            status_counts[status] = status_counts.get(status, 0) + 1

        # Count tasks by column
        task_counts = {}
        total_tasks = 0
        for col in context['kanban'].get('columns', []):
            task_counts[col['name']] = col['task_count']
            total_tasks += col['task_count']

        flowchart_count = len(context['flowcharts'])

        return json.dumps({
            'racm_rows': racm_rows,
            'status_breakdown': status_counts,
            'total_tasks': total_tasks,
            'tasks_by_stage': task_counts,
            'flowcharts': flowchart_count
        })

    elif tool_name == "create_flowchart":
        # Create a Drawflow-compatible flowchart
        name = tool_input.get('name', 'new-flowchart').lower().replace(' ', '-')
        steps = tool_input.get('steps', [])
        risk_id = tool_input.get('risk_id', '')

        # Node templates for Drawflow
        node_templates = {
            'start': '<div class="node-title">START</div><input type="text" class="node-input" value="{label}" df-name>',
            'process': '<div class="node-title">PROCESS</div><input type="text" class="node-input" value="{label}" df-name><textarea class="node-textarea" placeholder="Description..." df-description>{description}</textarea>',
            'decision': '<div class="node-title">DECISION</div><input type="text" class="node-input" value="{label}" df-name><textarea class="node-textarea" placeholder="Criteria..." df-description>{description}</textarea>',
            'control': '<div class="node-title">CONTROL</div><input type="text" class="node-input" value="{label}" df-name><textarea class="node-textarea" placeholder="Control description..." df-description>{description}</textarea>',
            'end': '<div class="node-title">END</div><input type="text" class="node-input" value="{label}" df-name>',
        }

        node_config = {
            'start': {'inputs': 0, 'outputs': 1},
            'process': {'inputs': 1, 'outputs': 1},
            'decision': {'inputs': 1, 'outputs': 2},
            'control': {'inputs': 1, 'outputs': 1},
            'end': {'inputs': 1, 'outputs': 0},
        }

        # Build Drawflow data structure
        drawflow_data = {"drawflow": {"Home": {"data": {}}}}
        nodes = drawflow_data["drawflow"]["Home"]["data"]

        y_pos = 50
        prev_node_id = None

        for i, step in enumerate(steps):
            node_id = str(i + 1)
            node_type = step.get('type', 'process')
            label = step.get('label', 'Step')
            description = step.get('description', '')

            config = node_config.get(node_type, {'inputs': 1, 'outputs': 1})
            template = node_templates.get(node_type, node_templates['process'])
            html = template.format(label=label, description=description)

            # Build inputs
            inputs = {}
            if config['inputs'] > 0:
                inputs["input_1"] = {"connections": []}
                if prev_node_id:
                    inputs["input_1"]["connections"].append({
                        "node": prev_node_id,
                        "input": "output_1"
                    })

            # Build outputs
            outputs = {}
            for j in range(config['outputs']):
                outputs[f"output_{j+1}"] = {"connections": []}

            nodes[node_id] = {
                "id": int(node_id),
                "name": node_type,
                "data": {"name": label, "description": description},
                "class": node_type,
                "html": html,
                "typenode": False,
                "inputs": inputs,
                "outputs": outputs,
                "pos_x": 150,
                "pos_y": y_pos
            }

            # Connect previous node to this one
            if prev_node_id and prev_node_id in nodes:
                nodes[prev_node_id]["outputs"]["output_1"]["connections"].append({
                    "node": node_id,
                    "output": "input_1"
                })

            prev_node_id = node_id
            y_pos += 150

        # Save flowchart
        flowchart_data[name] = drawflow_data
        data_version += 1

        # Link to RACM row if risk_id provided
        linked_msg = ""
        if risk_id:
            risk_id_upper = risk_id.upper()
            for row in spreadsheet_data[1:]:  # Skip header
                if row[0].upper() == risk_id_upper:
                    row[6] = name  # Set Flowchart column (index 6)
                    linked_msg = f" Linked to RACM row {risk_id_upper}."
                    break

        return f"Successfully created flowchart '{name}' with {len(steps)} nodes.{linked_msg} View at: /flowchart/{name}"

    return "Unknown tool"

@app.route('/api/chat/clear', methods=['POST'])
def clear_chat():
    global chat_history
    chat_history = []
    return jsonify({'status': 'cleared'})

def gather_audit_context():
    """Gather all audit data for AI context"""
    # RACM data
    racm = {
        'headers': spreadsheet_data[0] if spreadsheet_data else [],
        'rows': []
    }
    for i, row in enumerate(spreadsheet_data[1:], 1):
        if any(cell for cell in row):  # Skip empty rows
            row_dict = {}
            for j, header in enumerate(racm['headers']):
                row_dict[header] = row[j] if j < len(row) else ''
            racm['rows'].append(row_dict)

    # Kanban data
    kanban = kanban_data['boards'].get('default', {})

    # Summarize kanban for context
    kanban_summary = {'columns': []}
    if kanban and 'columns' in kanban:
        for col in kanban['columns']:
            col_summary = {
                'name': col['title'],
                'task_count': len(col['items']),
                'tasks': [{'title': item['title'], 'priority': item.get('priority', ''), 'assignee': item.get('assignee', '')} for item in col['items']]
            }
            kanban_summary['columns'].append(col_summary)

    # Flowcharts summary
    flowcharts_summary = {}
    for name, data in flowchart_data.items():
        if data and 'drawflow' in data:
            nodes = []
            for module_name, module in data['drawflow'].items():
                if 'data' in module:
                    for node_id, node in module['data'].items():
                        nodes.append({
                            'type': node.get('name', ''),
                            'data': node.get('data', {})
                        })
            flowcharts_summary[name] = {'node_count': len(nodes), 'nodes': nodes}

    return {
        'racm': racm,
        'kanban': kanban_summary,
        'flowcharts': flowcharts_summary
    }

if __name__ == '__main__':
    app.run(debug=True, port=8002)
