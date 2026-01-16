"""
Seed Data Script for SmartPapers

Creates representative dummy data for multiple audits including:
- Audits in the Annual Audit Plan
- RACM entries (risks and controls)
- Issues
- Kanban tasks
- Flowcharts

Run with: python3 seed_data.py
"""

from database import get_db
import json
from datetime import datetime, timedelta
import random

def seed_audits(db):
    """Create sample audits in the Annual Audit Plan."""
    audits = [
        {
            'title': 'SOX Compliance 2026',
            'description': 'Annual SOX 404 compliance audit covering key financial controls including revenue recognition, financial close, journal entries, and account reconciliations. Testing design and operating effectiveness per PCAOB AS 2201.',
            'audit_area': 'Finance',
            'owner': 'Sarah Chen',
            'planned_start': '2026-01-15',
            'planned_end': '2026-03-31',
            'actual_start': '2026-01-15',
            'actual_end': None,
            'quarter': 'Q1',
            'status': 'In Progress',
            'priority': 'high',
            'estimated_hours': 480,
            'actual_hours': 245,
            'risk_rating': 'High',
            'notes': 'Year 2 of SOX compliance. Focus areas: Revenue recognition (ASC 606), Manual journal entries, Management review controls. External auditors: Deloitte.'
        },
        {
            'title': 'IT General Controls',
            'description': 'Review of IT general controls supporting financial reporting systems. Scope includes logical access, change management, computer operations, and program development for ERP (Oracle), HR (Workday), and CRM (Salesforce).',
            'audit_area': 'Information Technology',
            'owner': 'Michael Torres',
            'planned_start': '2026-02-01',
            'planned_end': '2026-04-15',
            'actual_start': '2026-02-03',
            'actual_end': None,
            'quarter': 'Q1',
            'status': 'Fieldwork',
            'priority': 'high',
            'estimated_hours': 320,
            'actual_hours': 128,
            'risk_rating': 'Medium',
            'notes': 'Coordinating with SOX audit for integrated testing. CyberArk PAM implementation completed Q4 2025 - first year in scope. ServiceNow change management workflow updates pending review.'
        },
        {
            'title': 'Revenue Cycle Audit',
            'description': 'End-to-end review of revenue recognition, billing, and collections processes. Coverage includes order-to-cash, credit management, revenue cutoff, deferred revenue, and bad debt reserves.',
            'audit_area': 'Sales & Finance',
            'owner': 'Jennifer Adams',
            'planned_start': '2026-03-01',
            'planned_end': '2026-05-15',
            'actual_start': None,
            'actual_end': None,
            'quarter': 'Q1-Q2',
            'status': 'Planning',
            'priority': 'high',
            'estimated_hours': 400,
            'actual_hours': 24,
            'risk_rating': 'High',
            'notes': 'New product launch in Q2 - complex bundled arrangements. ASC 606 variable consideration estimates to be tested. Coordination needed with external auditors on revenue testing.'
        },
        {
            'title': 'Vendor Management Review',
            'description': 'Assessment of third-party vendor oversight including vendor risk assessment, due diligence, contract compliance, SLA monitoring, and fourth-party risk. Focus on critical and high-risk vendors.',
            'audit_area': 'Procurement',
            'owner': 'David Park',
            'planned_start': '2026-04-01',
            'planned_end': '2026-05-31',
            'actual_start': None,
            'actual_end': None,
            'quarter': 'Q2',
            'status': 'Not Started',
            'priority': 'medium',
            'estimated_hours': 240,
            'actual_hours': 0,
            'risk_rating': 'Medium',
            'notes': 'Vendor inventory: 247 total, 12 critical, 35 high-risk. New vendor management platform (OneTrust) implemented - first full year review. Cloud vendor concentration risk to be assessed.'
        },
        {
            'title': 'Cybersecurity Assessment',
            'description': 'Comprehensive review of cybersecurity controls covering network security, endpoint protection, vulnerability management, security monitoring, incident response, and data protection. Alignment to NIST CSF and CIS Controls.',
            'audit_area': 'Information Security',
            'owner': 'Michael Torres',
            'planned_start': '2026-05-01',
            'planned_end': '2026-07-31',
            'actual_start': None,
            'actual_end': None,
            'quarter': 'Q2-Q3',
            'status': 'Not Started',
            'priority': 'critical',
            'estimated_hours': 520,
            'actual_hours': 0,
            'risk_rating': 'Critical',
            'notes': 'Annual cybersecurity assessment required by cyber insurance policy. Penetration test scheduled for June. SOC 2 Type II audit running in parallel. Board presentation scheduled for August.'
        }
    ]

    audit_ids = []
    for audit in audits:
        # Check if audit already exists
        existing = db.get_all_audits()
        if any(a['title'] == audit['title'] for a in existing):
            # Get the existing audit ID
            for a in existing:
                if a['title'] == audit['title']:
                    audit_ids.append(a['id'])
                    break
            continue

        audit_id = db.create_audit(
            title=audit['title'],
            description=audit['description'],
            audit_area=audit['audit_area'],
            owner=audit['owner'],
            planned_start=audit['planned_start'],
            planned_end=audit['planned_end'],
            actual_start=audit.get('actual_start'),
            actual_end=audit.get('actual_end'),
            quarter=audit['quarter'],
            status=audit['status'],
            priority=audit['priority'],
            estimated_hours=audit['estimated_hours'],
            actual_hours=audit['actual_hours'],
            risk_rating=audit['risk_rating'],
            notes=audit['notes']
        )
        audit_ids.append(audit_id)
        print(f"  Created audit: {audit['title']} (ID: {audit_id})")

    return audit_ids


def seed_sox_audit(db, audit_id):
    """Seed RACM and issues for SOX Compliance audit."""
    risks = [
        {
            'risk_id': 'SOX-R001',
            'risk': 'Financial statements may contain material misstatements due to inadequate review controls',
            'control_id': 'Management review of monthly financial close package including variance analysis',
            'control_owner': 'CFO',
            'status': 'Complete',
            'design_effectiveness_testing': 'Obtained and inspected the Financial Close Checklist template. Verified the checklist includes: (1) completion sign-off by preparer, (2) variance analysis threshold of 10%, (3) management review signature line, (4) date fields for each step. Confirmed the checklist is embedded in the ERP system closing module.',
            'design_effectiveness_conclusion': 'Effective - The control is appropriately designed to address the risk. The checklist enforces systematic review steps and requires documented variance explanations for any items exceeding 10% threshold.',
            'operational_effectiveness_test': 'Selected a sample of 12 monthly close packages (Jan-Dec 2025). For each package: (1) Verified preparer completed all checklist items, (2) Confirmed variance analysis was documented for items >10%, (3) Verified CFO signature and date within 5 business days of month-end. Results: 12/12 packages had complete checklists. 8/12 had variances requiring explanation - all were documented. All 12 had timely CFO review.',
            'operational_effectiveness_conclusion': 'Effective - Based on testing of 12 months of close packages, the control operated effectively throughout the audit period. No exceptions noted.'
        },
        {
            'risk_id': 'SOX-R002',
            'risk': 'Unauthorized journal entries could be posted without proper approval',
            'control_id': 'All journal entries over $10,000 require dual approval in the ERP system',
            'control_owner': 'Controller',
            'status': 'In Progress',
            'design_effectiveness_testing': 'Inspected ERP system configuration for journal entry workflow. Confirmed: (1) Threshold set at $10,000 for secondary approval, (2) Workflow routes to Controller for entries >$10K, (3) System prevents posting without required approvals, (4) Audit trail captures approver ID and timestamp.',
            'design_effectiveness_conclusion': 'Effective - System enforced controls appropriately designed to prevent unauthorized journal entries above threshold.',
            'operational_effectiveness_test': 'Obtained population of 1,247 journal entries >$10,000 for the period. Selected sample of 25 entries using random sampling. For each entry: verified (1) dual approval obtained, (2) approvers had appropriate authority, (3) approval obtained prior to posting. EXCEPTION: 3 entries were posted with only single approval due to a system configuration issue in March that was subsequently corrected.',
            'operational_effectiveness_conclusion': 'Ineffective - 3/25 (12%) sample items lacked required dual approval. Control deficiency identified and reported to management. See Issue SOX-I001.'
        },
        {
            'risk_id': 'SOX-R003',
            'risk': 'Revenue may be recognized in incorrect periods',
            'control_id': 'Revenue recognition review performed monthly with cutoff testing',
            'control_owner': 'Revenue Accounting Manager',
            'status': 'Complete',
            'design_effectiveness_testing': 'Reviewed Revenue Cutoff Procedure and month-end close checklist. Cutoff testing includes: (1) Review of sales orders shipped +/- 3 days of period end, (2) Verification of delivery dates to shipping documentation, (3) Revenue timing validation against contract terms. Documented in Oracle revenue recognition module.',
            'design_effectiveness_conclusion': 'Effective - Cutoff procedures designed to ensure revenue recognized in correct period.',
            'operational_effectiveness_test': 'Tested revenue cutoff for Jun, Jul, Aug 2025 close. Selected 30 transactions per month near period end (90 total). Verified ship dates to BOL/POD documentation. 88/90 properly recorded in correct period. 2 exceptions <$5K, immaterial, documented and corrected.',
            'operational_effectiveness_conclusion': 'Effective - Revenue cutoff controls operating effectively with immaterial exceptions noted.'
        },
        {
            'risk_id': 'SOX-R004',
            'risk': 'Account reconciliations may not identify errors timely',
            'control_id': 'Monthly reconciliation of all balance sheet accounts with supervisory review',
            'control_owner': 'Accounting Manager',
            'status': 'Complete',
            'design_effectiveness_testing': 'Obtained reconciliation policy and template. Verified policy requires: (1) reconciliation within 5 business days of month-end, (2) documented explanation for all reconciling items >$1,000, (3) supervisor review and sign-off. Template includes all required fields.',
            'design_effectiveness_conclusion': 'Effective - Policy and template appropriately designed to identify and resolve account differences timely.',
            'operational_effectiveness_test': 'Selected 15 balance sheet accounts representing 85% of total assets. For each account, tested reconciliations for 3 months (Q3 2025). Verified: (1) reconciliation completed within 5 days - 44/45 compliant, (2) reconciling items explained - all compliant, (3) supervisor review documented - 45/45 compliant. One late reconciliation was for Prepaid Expenses in August (completed day 7) due to staff vacation.',
            'operational_effectiveness_conclusion': 'Effective - Minor timing exception (1/45 = 2%) does not indicate control failure. Overall control operating effectively.'
        },
        {
            'risk_id': 'SOX-R005',
            'risk': 'Segregation of duties violations in financial systems',
            'control_id': 'Quarterly access review of financial system roles and permissions',
            'control_owner': 'IT Security Manager',
            'status': 'In Progress',
            'design_effectiveness_testing': 'Reviewed access review procedure document. Procedure includes: (1) extraction of user access report from ERP, (2) distribution to department managers, (3) manager certification of appropriateness, (4) removal of inappropriate access within 5 days. SOD conflict matrix maintained and reviewed.',
            'design_effectiveness_conclusion': 'Effective - Access review process appropriately designed to identify and remediate SOD conflicts.',
            'operational_effectiveness_test': 'Testing in progress - awaiting Q4 access review completion.',
            'operational_effectiveness_conclusion': ''
        }
    ]

    risk_ids = []
    for risk in risks:
        row_id = db.create_risk(
            risk_id=risk['risk_id'],
            risk=risk['risk'],
            control_id=risk['control_id'],
            control_owner=risk['control_owner'],
            status=risk['status']
        )
        # Update audit_id and DE/OE fields
        conn = db._get_conn()
        conn.execute("""UPDATE risks SET
            audit_id = ?,
            design_effectiveness_testing = ?,
            design_effectiveness_conclusion = ?,
            operational_effectiveness_test = ?,
            operational_effectiveness_conclusion = ?
            WHERE id = ?""", (
            audit_id,
            risk.get('design_effectiveness_testing', ''),
            risk.get('design_effectiveness_conclusion', ''),
            risk.get('operational_effectiveness_test', ''),
            risk.get('operational_effectiveness_conclusion', ''),
            row_id
        ))
        conn.commit()
        conn.close()
        risk_ids.append(row_id)

    # Create test documents (DE/OE rich text working papers) for completed controls
    test_documents = [
        {
            'risk_id': 'SOX-R001',
            'de_content': '''<h2>Design Effectiveness Testing - SOX-R001</h2>
<h3>Control: Management Review of Monthly Financial Close</h3>
<p><strong>Test Objective:</strong> Verify the control is appropriately designed to ensure timely review of financial close packages.</p>
<h3>Testing Procedures:</h3>
<ol>
<li>Obtained Financial Close Checklist template from the Controller</li>
<li>Reviewed checklist for completeness of required elements</li>
<li>Confirmed checklist is system-enforced in ERP closing module</li>
<li>Interviewed CFO regarding review process</li>
</ol>
<h3>Evidence Obtained:</h3>
<ul>
<li>Financial Close Checklist v3.2 (Ref: WP-SOX-001-A)</li>
<li>Screenshot of ERP closing module workflow configuration</li>
<li>CFO interview notes dated 2025-10-15</li>
</ul>
<h3>Conclusion:</h3>
<p style="color: green;"><strong>EFFECTIVE</strong> - Control design adequately addresses the identified risk.</p>''',
            'oe_content': '''<h2>Operational Effectiveness Testing - SOX-R001</h2>
<h3>Control: Management Review of Monthly Financial Close</h3>
<p><strong>Test Period:</strong> January 2025 - December 2025</p>
<p><strong>Population:</strong> 12 monthly close packages</p>
<p><strong>Sample Size:</strong> 12 (100% - full population tested)</p>
<h3>Testing Procedures:</h3>
<ol>
<li>Obtained all 12 monthly close packages from Accounting</li>
<li>For each package, verified preparer sign-off was documented</li>
<li>Confirmed variance analysis was performed for items &gt;10%</li>
<li>Verified CFO review signature and date within 5 business days</li>
</ol>
<h3>Testing Results:</h3>
<table border="1" cellpadding="5">
<tr><th>Month</th><th>Preparer Sign-off</th><th>Variance Analysis</th><th>CFO Review</th><th>Timely</th></tr>
<tr><td>Jan 2025</td><td>✓</td><td>N/A</td><td>✓</td><td>Day 3</td></tr>
<tr><td>Feb 2025</td><td>✓</td><td>✓ (2 items)</td><td>✓</td><td>Day 4</td></tr>
<tr><td>Mar 2025</td><td>✓</td><td>✓ (1 item)</td><td>✓</td><td>Day 5</td></tr>
<tr><td>Apr 2025</td><td>✓</td><td>N/A</td><td>✓</td><td>Day 2</td></tr>
<tr><td>May 2025</td><td>✓</td><td>✓ (3 items)</td><td>✓</td><td>Day 4</td></tr>
<tr><td>Jun 2025</td><td>✓</td><td>✓ (2 items)</td><td>✓</td><td>Day 3</td></tr>
<tr><td>Jul 2025</td><td>✓</td><td>N/A</td><td>✓</td><td>Day 3</td></tr>
<tr><td>Aug 2025</td><td>✓</td><td>✓ (1 item)</td><td>✓</td><td>Day 5</td></tr>
<tr><td>Sep 2025</td><td>✓</td><td>N/A</td><td>✓</td><td>Day 2</td></tr>
<tr><td>Oct 2025</td><td>✓</td><td>✓ (4 items)</td><td>✓</td><td>Day 4</td></tr>
<tr><td>Nov 2025</td><td>✓</td><td>✓ (2 items)</td><td>✓</td><td>Day 3</td></tr>
<tr><td>Dec 2025</td><td>✓</td><td>✓ (3 items)</td><td>✓</td><td>Day 5</td></tr>
</table>
<h3>Exceptions:</h3>
<p>None noted.</p>
<h3>Conclusion:</h3>
<p style="color: green;"><strong>EFFECTIVE</strong> - Control operated effectively throughout the test period.</p>'''
        },
        {
            'risk_id': 'SOX-R002',
            'de_content': '''<h2>Design Effectiveness Testing - SOX-R002</h2>
<h3>Control: Dual Approval for Journal Entries &gt;$10,000</h3>
<p><strong>Test Objective:</strong> Verify system configuration enforces dual approval requirement.</p>
<h3>Testing Procedures:</h3>
<ol>
<li>Obtained ERP system configuration documentation</li>
<li>Observed workflow settings for journal entry approval</li>
<li>Tested control by attempting to post $15,000 JE with single approval</li>
<li>Reviewed audit trail settings</li>
</ol>
<h3>Evidence Obtained:</h3>
<ul>
<li>ERP Workflow Configuration Report (Ref: WP-SOX-002-A)</li>
<li>Screenshot showing system rejection of single-approval JE</li>
<li>Audit trail sample showing approver details</li>
</ul>
<h3>Conclusion:</h3>
<p style="color: green;"><strong>EFFECTIVE</strong> - System configuration appropriately prevents posting without dual approval.</p>''',
            'oe_content': '''<h2>Operational Effectiveness Testing - SOX-R002</h2>
<h3>Control: Dual Approval for Journal Entries &gt;$10,000</h3>
<p><strong>Test Period:</strong> January 2025 - September 2025</p>
<p><strong>Population:</strong> 1,247 journal entries exceeding $10,000</p>
<p><strong>Sample Size:</strong> 25 (using MUS sampling)</p>
<h3>Testing Procedures:</h3>
<ol>
<li>Obtained full population from ERP system</li>
<li>Selected sample using monetary unit sampling</li>
<li>For each item, verified dual approval was obtained</li>
<li>Confirmed approvers had appropriate authority</li>
<li>Verified approval timestamps precede posting</li>
</ol>
<h3>Testing Results:</h3>
<table border="1" cellpadding="5">
<tr><th>Sample #</th><th>JE Amount</th><th>Approver 1</th><th>Approver 2</th><th>Result</th></tr>
<tr><td>1</td><td>$45,230</td><td>Controller</td><td>CFO</td><td>✓</td></tr>
<tr><td>2</td><td>$18,500</td><td>AP Manager</td><td>Controller</td><td>✓</td></tr>
<tr><td>3</td><td>$125,000</td><td>Controller</td><td>CFO</td><td>✓</td></tr>
<tr><td>4</td><td>$22,750</td><td>Controller</td><td>-</td><td style="color:red;">✗ EXCEPTION</td></tr>
<tr><td>5</td><td>$31,200</td><td>AP Manager</td><td>Controller</td><td>✓</td></tr>
<tr><td>...</td><td colspan="4">Additional 17 items tested - all compliant</td></tr>
<tr><td>23</td><td>$15,800</td><td>Controller</td><td>-</td><td style="color:red;">✗ EXCEPTION</td></tr>
<tr><td>24</td><td>$28,900</td><td>Controller</td><td>-</td><td style="color:red;">✗ EXCEPTION</td></tr>
<tr><td>25</td><td>$52,100</td><td>Controller</td><td>CFO</td><td>✓</td></tr>
</table>
<h3>Exceptions Identified:</h3>
<p style="color: red;"><strong>3 exceptions noted (items 4, 23, 24)</strong> - Journal entries posted with single approval only.</p>
<p>Root cause: System configuration was temporarily modified on March 15, 2025 during an ERP upgrade. The dual approval setting was inadvertently disabled and not restored until March 22, 2025. All 3 exceptions occurred during this window.</p>
<h3>Management Response:</h3>
<p>Configuration has been corrected and change control procedures updated to include verification of approval workflow settings post-upgrade.</p>
<h3>Conclusion:</h3>
<p style="color: red;"><strong>INEFFECTIVE</strong> - Control did not operate effectively during March 2025. Issue raised - see SOX-I001.</p>'''
        }
    ]

    # Insert test documents
    for doc in test_documents:
        # Find the risk ID
        conn = db._get_conn()
        row = conn.execute("SELECT id FROM risks WHERE risk_id = ?", (doc['risk_id'],)).fetchone()
        if row:
            risk_db_id = row['id']
            # Insert DE testing document
            conn.execute("""INSERT OR REPLACE INTO test_documents (risk_id, doc_type, content, audit_id)
                VALUES (?, 'de_testing', ?, ?)""", (risk_db_id, doc['de_content'], audit_id))
            # Insert OE testing document
            conn.execute("""INSERT OR REPLACE INTO test_documents (risk_id, doc_type, content, audit_id)
                VALUES (?, 'oe_testing', ?, ?)""", (risk_db_id, doc['oe_content'], audit_id))
            conn.commit()
        conn.close()

    # Create issues for this audit
    issues = [
        {
            'title': 'Journal Entry Approval Bypass',
            'description': 'Found 3 instances where journal entries over $10,000 were posted with single approval',
            'risk_id': 'SOX-R002',
            'severity': 'High',
            'status': 'Open',
            'assigned_to': 'Controller'
        },
        {
            'title': 'Late Account Reconciliations',
            'description': '2 balance sheet accounts were not reconciled within the 5-day deadline',
            'risk_id': 'SOX-R004',
            'severity': 'Medium',
            'status': 'In Progress',
            'assigned_to': 'Accounting Manager'
        }
    ]

    for issue in issues:
        issue_id = db.create_issue(
            title=issue['title'],
            description=issue['description'],
            risk_id=issue['risk_id'],
            severity=issue['severity'],
            status=issue['status'],
            assigned_to=issue['assigned_to']
        )
        # Get the row id from the issue_id
        conn = db._get_conn()
        row = conn.execute("SELECT id FROM issues WHERE issue_id = ?", (issue_id,)).fetchone()
        if row:
            conn.execute("UPDATE issues SET audit_id = ? WHERE id = ?", (audit_id, row['id']))
            conn.commit()
        conn.close()

    # Create tasks
    tasks = [
        {'title': 'Review JE approval documentation', 'description': 'Pull sample of 25 JEs for testing', 'column_id': 'fieldwork', 'priority': 'high'},
        {'title': 'Test revenue cutoff', 'description': 'Select transactions around period end', 'column_id': 'planning', 'priority': 'medium'},
        {'title': 'Update control matrix', 'description': 'Document control changes from prior year', 'column_id': 'complete', 'priority': 'low'},
    ]

    for task in tasks:
        task_id = db.create_task(
            title=task['title'],
            description=task['description'],
            column_id=task['column_id'],
            priority=task['priority']
        )
        conn = db._get_conn()
        conn.execute("UPDATE tasks SET audit_id = ? WHERE id = ?", (audit_id, task_id))
        conn.commit()
        conn.close()

    print(f"  Added {len(risks)} risks, {len(issues)} issues, {len(tasks)} tasks, {len(test_documents)} test documents to SOX audit")


def seed_itgc_audit(db, audit_id):
    """Seed RACM and issues for IT General Controls audit."""
    risks = [
        {
            'risk_id': 'ITGC-R001',
            'risk': 'Unauthorized access to production systems due to weak access controls',
            'control_id': 'Quarterly access review with manager certification of user access rights',
            'control_owner': 'IT Security Manager',
            'status': 'In Progress',
            'design_effectiveness_testing': 'Reviewed User Access Review Procedure v2.1. Confirmed: (1) AD user listing extracted quarterly, (2) Manager certification forms distributed, (3) 10-day response deadline, (4) IT removes uncertified access within 5 days. Evidence: Procedure document and sample certification form.',
            'design_effectiveness_conclusion': 'Effective - Process designed to ensure periodic validation of user access rights.',
            'operational_effectiveness_test': 'Obtained Q1-Q3 2025 access review packages. Tested 100% of reviews. Q1: 247 users reviewed, 12 removed. Q2: 251 users, 8 removed. Q3: 245 users, 15 removed. All certifications completed within deadline.',
            'operational_effectiveness_conclusion': 'Testing in progress - Q4 review pending.'
        },
        {
            'risk_id': 'ITGC-R002',
            'risk': 'Unapproved changes to production code could introduce errors or vulnerabilities',
            'control_id': 'Change management process with CAB approval and segregated deployment',
            'control_owner': 'IT Operations Manager',
            'status': 'Complete',
            'design_effectiveness_testing': 'Reviewed Change Management Policy v3.2 and ServiceNow change workflow. Key elements: (1) RFC submission with business justification, (2) CAB review for standard/major changes, (3) Segregated deployment team, (4) Post-implementation verification. Emergency change process documented with retrospective CAB review.',
            'design_effectiveness_conclusion': 'Effective - Change management process comprehensively designed with appropriate approval gates and segregation.',
            'operational_effectiveness_test': 'Selected 25 changes from Jan-Sep 2025 (15 standard, 7 major, 3 emergency). All 22 standard/major had CAB approval before deployment. 3 emergency changes had documented retrospective review. Verified deployment performed by separate team from developers in all cases.',
            'operational_effectiveness_conclusion': 'Effective - Change management controls operating as designed with proper approvals and segregation.'
        },
        {
            'risk_id': 'ITGC-R003',
            'risk': 'System outages due to inadequate backup and recovery procedures',
            'control_id': 'Daily backups with monthly restoration testing and documented recovery plans',
            'control_owner': 'Infrastructure Manager',
            'status': 'Complete',
            'design_effectiveness_testing': 'Reviewed Backup and Recovery Procedure and Veeam configuration. Daily incremental backups at 2am, weekly full backups Saturday 11pm. Monthly restoration test of random file sets. Recovery plans documented for Tier 1 systems with 4-hour RTO, Tier 2 with 24-hour RTO.',
            'design_effectiveness_conclusion': 'Effective - Backup procedures appropriately designed with defined RTOs and regular testing.',
            'operational_effectiveness_test': 'Obtained backup job logs for Jan-Sep 2025. 273 daily jobs, 267 successful (98%). 6 failures resolved within 24 hours with successful re-run. Monthly restoration tests completed for all 9 months with 100% success rate. Reviewed 3 actual recovery events - all within RTO.',
            'operational_effectiveness_conclusion': 'Effective - Backup and recovery processes operating effectively with high success rates.'
        },
        {
            'risk_id': 'ITGC-R004',
            'risk': 'Privileged access abuse by system administrators',
            'control_id': 'Privileged access management (PAM) solution with session recording',
            'control_owner': 'IT Security Manager',
            'status': 'Complete',
            'design_effectiveness_testing': 'Reviewed CyberArk PAM configuration. Session recording enabled for all privileged accounts. Dual authorization required for domain admin access. Audit logs retained for 2 years. Password vault rotation every 30 days for service accounts.',
            'design_effectiveness_conclusion': 'Effective - PAM solution appropriately configured to monitor and control privileged access.',
            'operational_effectiveness_test': 'Sampled 20 privileged sessions from CyberArk logs (Jul-Sep 2025). All sessions recorded with video playback available. Tested 5 domain admin requests - all required dual approval. Verified password rotation logs showing 100% compliance with 30-day policy.',
            'operational_effectiveness_conclusion': 'Effective - PAM controls operating as designed with full session recording and dual approval enforcement.'
        },
        {
            'risk_id': 'ITGC-R005',
            'risk': 'Data loss from terminated employee accounts not disabled timely',
            'control_id': 'HR-IT integration for automated account disablement within 24 hours',
            'control_owner': 'HR Systems Manager',
            'status': 'Complete',
            'design_effectiveness_testing': 'Reviewed Workday-AD integration architecture. Termination trigger in Workday initiates automated workflow to disable AD account. Email to manager confirms deactivation. Weekly reconciliation report compares HR terminations to AD disabled accounts.',
            'design_effectiveness_conclusion': 'Effective - Automated integration designed to ensure timely account disablement with reconciliation controls.',
            'operational_effectiveness_test': 'Obtained termination list from HR (87 employees Jan-Sep 2025). Compared to AD disabled dates. 85/87 (98%) disabled within 24 hours. 2 exceptions: 1 contractor (manual process) disabled in 48 hours, 1 system error corrected in 36 hours. Both documented.',
            'operational_effectiveness_conclusion': 'Effective - Account disablement process operating with 98% compliance to SLA.'
        },
        {
            'risk_id': 'ITGC-R006',
            'risk': 'Batch job failures may go undetected',
            'control_id': 'Automated monitoring of critical batch jobs with alerting to operations team',
            'control_owner': 'IT Operations Manager',
            'status': 'Complete',
            'design_effectiveness_testing': 'Reviewed SolarWinds job monitoring configuration. 47 critical batch jobs defined with success/failure thresholds. Alerts sent to ops-alerts@company.com and ServiceNow ticket auto-created. Escalation to manager if not acknowledged within 30 minutes.',
            'design_effectiveness_conclusion': 'Effective - Monitoring configured for all critical batch jobs with appropriate alerting and escalation.',
            'operational_effectiveness_test': 'Reviewed batch job monitoring dashboard for Aug-Sep 2025. 2,847 job executions, 41 failures detected (1.4%). All 41 generated alerts within 2 minutes. ServiceNow tickets created for all. Average resolution time 47 minutes. No failures went undetected.',
            'operational_effectiveness_conclusion': 'Effective - Batch job monitoring operating with 100% detection rate and timely resolution.'
        }
    ]

    for risk in risks:
        row_id = db.create_risk(
            risk_id=risk['risk_id'],
            risk=risk['risk'],
            control_id=risk['control_id'],
            control_owner=risk['control_owner'],
            status=risk['status']
        )
        conn = db._get_conn()
        conn.execute("""UPDATE risks SET
            audit_id = ?,
            design_effectiveness_testing = ?,
            design_effectiveness_conclusion = ?,
            operational_effectiveness_test = ?,
            operational_effectiveness_conclusion = ?
            WHERE id = ?""", (
            audit_id,
            risk.get('design_effectiveness_testing', ''),
            risk.get('design_effectiveness_conclusion', ''),
            risk.get('operational_effectiveness_test', ''),
            risk.get('operational_effectiveness_conclusion', ''),
            row_id
        ))
        conn.commit()
        conn.close()

    # Create issues
    issues = [
        {
            'title': 'Stale User Accounts',
            'description': '15 user accounts found with no login activity in 90+ days still active',
            'risk_id': 'ITGC-R001',
            'severity': 'Medium',
            'status': 'Open',
            'assigned_to': 'IT Security Manager'
        }
    ]

    for issue in issues:
        issue_id = db.create_issue(
            title=issue['title'],
            description=issue['description'],
            risk_id=issue['risk_id'],
            severity=issue['severity'],
            status=issue['status'],
            assigned_to=issue['assigned_to']
        )
        # Get the row id from the issue_id
        conn = db._get_conn()
        row = conn.execute("SELECT id FROM issues WHERE issue_id = ?", (issue_id,)).fetchone()
        if row:
            conn.execute("UPDATE issues SET audit_id = ? WHERE id = ?", (audit_id, row['id']))
            conn.commit()
        conn.close()

    # Create test documents
    test_documents = [
        {
            'risk_id': 'ITGC-R001',
            'de_content': '''<h2>Design Effectiveness Testing - ITGC-R001</h2>
<h3>Control: Quarterly User Access Review</h3>
<p><strong>Test Objective:</strong> Verify the access review process is designed to identify and remove inappropriate access.</p>
<h3>Process Documentation Reviewed:</h3>
<ul>
<li>User Access Review Procedure v2.1</li>
<li>Manager Certification Form template</li>
<li>IT Access Removal Checklist</li>
</ul>
<h3>Key Control Elements:</h3>
<table border="1" cellpadding="5">
<tr><th>Element</th><th>Design</th><th>Assessment</th></tr>
<tr><td>Frequency</td><td>Quarterly</td><td>Adequate</td></tr>
<tr><td>Scope</td><td>All AD users + key applications</td><td>Adequate</td></tr>
<tr><td>Manager Certification</td><td>10-day response deadline</td><td>Adequate</td></tr>
<tr><td>Removal Timeliness</td><td>5 days from certification</td><td>Adequate</td></tr>
<tr><td>Documentation</td><td>Retained in ServiceNow</td><td>Adequate</td></tr>
</table>
<h3>Conclusion:</h3>
<p style="color: green;"><strong>EFFECTIVE</strong> - Access review process appropriately designed.</p>''',
            'oe_content': '''<h2>Operational Effectiveness Testing - ITGC-R001</h2>
<h3>Control: Quarterly User Access Review</h3>
<p><strong>Test Period:</strong> Q1-Q3 2025</p>
<h3>Review Completion Summary:</h3>
<table border="1" cellpadding="5">
<tr><th>Quarter</th><th>Users Reviewed</th><th>Access Removed</th><th>Completed On Time</th></tr>
<tr><td>Q1 2025</td><td>247</td><td>12</td><td style="color:green;">✓</td></tr>
<tr><td>Q2 2025</td><td>251</td><td>8</td><td style="color:green;">✓</td></tr>
<tr><td>Q3 2025</td><td>245</td><td>15</td><td style="color:green;">✓</td></tr>
</table>
<h3>Sample Testing (15 removed users):</h3>
<p>Verified AD account disabled within 5 business days of certification.</p>
<p><strong>Result:</strong> 15/15 accounts disabled timely.</p>
<h3>Conclusion:</h3>
<p style="color: orange;"><strong>TESTING IN PROGRESS</strong> - Q4 review pending completion.</p>'''
        },
        {
            'risk_id': 'ITGC-R004',
            'de_content': '''<h2>Design Effectiveness Testing - ITGC-R004</h2>
<h3>Control: Privileged Access Management (PAM)</h3>
<p><strong>Test Objective:</strong> Verify PAM solution is designed to control and monitor privileged access.</p>
<h3>CyberArk Configuration Review:</h3>
<table border="1" cellpadding="5">
<tr><th>Feature</th><th>Configuration</th><th>Assessment</th></tr>
<tr><td>Session Recording</td><td>Enabled for all privileged accounts</td><td style="color:green;">Adequate</td></tr>
<tr><td>Password Rotation</td><td>Every 30 days automatic</td><td style="color:green;">Adequate</td></tr>
<tr><td>Dual Authorization</td><td>Required for domain admin</td><td style="color:green;">Adequate</td></tr>
<tr><td>Just-in-Time Access</td><td>4-hour checkout maximum</td><td style="color:green;">Adequate</td></tr>
<tr><td>Audit Logging</td><td>2-year retention</td><td style="color:green;">Adequate</td></tr>
</table>
<h3>Privileged Account Inventory:</h3>
<ul>
<li>Domain Admins: 8 accounts</li>
<li>Database Admins: 12 accounts</li>
<li>Server Admins: 24 accounts</li>
<li>Application Service Accounts: 47 accounts</li>
</ul>
<h3>Conclusion:</h3>
<p style="color: green;"><strong>EFFECTIVE</strong> - PAM solution comprehensively configured.</p>''',
            'oe_content': '''<h2>Operational Effectiveness Testing - ITGC-R004</h2>
<h3>Control: Privileged Access Management (PAM)</h3>
<p><strong>Test Period:</strong> 2025</p>
<h3>Testing Procedures:</h3>
<ol>
<li>Reviewed PAM session recordings for sample of privileged activities</li>
<li>Verified password rotation occurred per policy</li>
<li>Tested dual authorization for domain admin checkouts</li>
<li>Reviewed audit logs for anomalies</li>
</ol>
<h3>Testing pending - awaiting scheduled PAM assessment in Q4.</h3>
<p><em>Note: Design testing complete. Operational testing scheduled for November 2025.</em></p>'''
        }
    ]

    for doc in test_documents:
        conn = db._get_conn()
        row = conn.execute("SELECT id FROM risks WHERE risk_id = ?", (doc['risk_id'],)).fetchone()
        if row:
            risk_db_id = row['id']
            conn.execute("""INSERT OR REPLACE INTO test_documents (risk_id, doc_type, content, audit_id)
                VALUES (?, 'de_testing', ?, ?)""", (risk_db_id, doc['de_content'], audit_id))
            conn.execute("""INSERT OR REPLACE INTO test_documents (risk_id, doc_type, content, audit_id)
                VALUES (?, 'oe_testing', ?, ?)""", (risk_db_id, doc['oe_content'], audit_id))
            conn.commit()
        conn.close()

    # Create tasks
    tasks = [
        {'title': 'Pull user access listing', 'description': 'Extract from Active Directory and key applications', 'column_id': 'complete', 'priority': 'high'},
        {'title': 'Review Q1-Q3 access reviews', 'description': 'Verify manager certifications and access removals', 'column_id': 'complete', 'priority': 'high'},
        {'title': 'Test change management', 'description': 'Sample 30 changes for CAB approval and testing', 'column_id': 'fieldwork', 'priority': 'high'},
        {'title': 'Review backup procedures', 'description': 'Obtain backup logs and restoration test results', 'column_id': 'fieldwork', 'priority': 'medium'},
        {'title': 'Test PAM controls', 'description': 'Review CyberArk configuration and session recordings', 'column_id': 'planning', 'priority': 'high'},
        {'title': 'Verify termination process', 'description': 'Test HR-IT integration for account disablement', 'column_id': 'planning', 'priority': 'medium'},
        {'title': 'Review batch job monitoring', 'description': 'Obtain evidence of automated monitoring and alerting', 'column_id': 'planning', 'priority': 'medium'},
        {'title': 'Draft ITGC findings', 'description': 'Prepare summary of control testing results', 'column_id': 'planning', 'priority': 'high'},
    ]

    for task in tasks:
        task_id = db.create_task(
            title=task['title'],
            description=task['description'],
            column_id=task['column_id'],
            priority=task['priority']
        )
        conn = db._get_conn()
        conn.execute("UPDATE tasks SET audit_id = ? WHERE id = ?", (audit_id, task_id))
        conn.commit()
        conn.close()

    print(f"  Added {len(risks)} risks, {len(issues)} issues, {len(tasks)} tasks, {len(test_documents)} test documents to ITGC audit")


def seed_revenue_audit(db, audit_id):
    """Seed RACM and issues for Revenue Cycle audit."""
    risks = [
        {
            'risk_id': 'REV-R001',
            'risk': 'Revenue recognized before performance obligations are satisfied',
            'control_id': 'Contract review checklist ensuring delivery/acceptance before revenue posting',
            'control_owner': 'Revenue Recognition Manager',
            'status': 'Complete',
            'design_effectiveness_testing': 'Obtained Contract Review Checklist template and ASC 606 Revenue Recognition Policy. Checklist includes: (1) identification of performance obligations, (2) transaction price determination, (3) allocation methodology, (4) delivery/acceptance evidence requirements, (5) manager sign-off before revenue posting. System enforces checklist completion in Oracle.',
            'design_effectiveness_conclusion': 'Effective - Checklist comprehensively designed to ensure ASC 606 compliance before revenue recognition.',
            'operational_effectiveness_test': 'Selected 25 revenue transactions >$50,000 from Q1-Q3 2025 (total population: 847). For each: verified checklist completion, performance obligation documentation, delivery evidence. 25/25 had complete checklists. 23/25 had delivery acceptance on file. 2 items were subscription revenue recognized over time - verified allocation methodology.',
            'operational_effectiveness_conclusion': 'Effective - Contract review process operating effectively with proper documentation of revenue recognition criteria.'
        },
        {
            'risk_id': 'REV-R002',
            'risk': 'Customer credits and returns not recorded timely',
            'control_id': 'Daily review of credit memo requests with 48-hour processing SLA',
            'control_owner': 'AR Manager',
            'status': 'Complete',
            'design_effectiveness_testing': 'Reviewed Credit Memo Processing Procedure. Process includes: (1) customer request logged in CRM, (2) AR team reviews within 24 hours, (3) approval workflow based on amount thresholds, (4) credit posted within 48 hours of approval, (5) daily aging report of pending credits reviewed by AR Manager.',
            'design_effectiveness_conclusion': 'Effective - Process designed to ensure timely processing and proper approval of customer credits.',
            'operational_effectiveness_test': 'Obtained population of 312 credit memos processed in Q2-Q3 2025. Tested sample of 30 credits. Verified: (1) 28/30 processed within 48-hour SLA, (2) all had proper approval per threshold, (3) all tied to valid customer request. 2 SLA misses were during month-end close - documented exceptions approved by Controller.',
            'operational_effectiveness_conclusion': 'Effective - Credit memo process operating effectively with minor documented exceptions during peak periods.'
        },
        {
            'risk_id': 'REV-R003',
            'risk': 'Unbilled revenue not identified and recorded',
            'control_id': 'Weekly unbilled revenue report review with follow-up on aged items',
            'control_owner': 'Billing Manager',
            'status': 'In Progress',
            'design_effectiveness_testing': 'Reviewed Unbilled Revenue Report and follow-up procedures. Report generated weekly from Oracle showing: (1) services delivered but not invoiced, (2) aging by days unbilled, (3) responsible account manager. Items >30 days require documented explanation. Billing Manager reviews and escalates items >60 days.',
            'design_effectiveness_conclusion': 'Effective - Weekly review process designed to identify and resolve unbilled revenue timely.',
            'operational_effectiveness_test': 'Testing in progress. Obtained unbilled revenue reports for Aug-Oct 2025. Average unbilled balance: $2.3M. Items >30 days: 12 averaging $45K each. Verifying documentation and resolution for aged items.',
            'operational_effectiveness_conclusion': ''
        },
        {
            'risk_id': 'REV-R004',
            'risk': 'Sales commissions calculated incorrectly',
            'control_id': 'Monthly commission calculation review with sales operations sign-off',
            'control_owner': 'Sales Operations Director',
            'status': 'Complete',
            'design_effectiveness_testing': 'Reviewed Commission Calculation Policy and Xactly system configuration. Commissions calculated based on: (1) deal size tiers, (2) product category rates, (3) quota attainment multipliers. System pulls revenue data from Oracle. Sales Ops reviews calculation report, validates sample deals, signs off before payroll submission.',
            'design_effectiveness_conclusion': 'Effective - Automated calculation with manual review provides appropriate controls over commission accuracy.',
            'operational_effectiveness_test': 'Tested commission calculations for 6 months (Apr-Sep 2025). For each month: verified system calculation matched policy rates, reviewed sign-off documentation, tested sample of 5 deals to source revenue. 30/30 sampled deals calculated correctly. All months had Sales Ops Director sign-off before payment.',
            'operational_effectiveness_conclusion': 'Effective - Commission calculations accurate with proper review and approval process.'
        },
        {
            'risk_id': 'REV-R005',
            'risk': 'Customer pricing errors in billing system',
            'control_id': 'Price change approval workflow with system update verification',
            'control_owner': 'Pricing Manager',
            'status': 'Complete',
            'design_effectiveness_testing': 'Reviewed Price Change Request workflow in ServiceNow. Process requires: (1) business justification, (2) margin impact analysis, (3) VP Sales approval for discounts >15%, (4) CFO approval for discounts >25%, (5) IT verification of Oracle price book update. Audit trail maintained for all changes.',
            'design_effectiveness_conclusion': 'Effective - Multi-level approval workflow with system verification ensures pricing changes are authorized and accurately implemented.',
            'operational_effectiveness_test': 'Obtained list of 67 price changes in 2025. Tested sample of 20 changes. Verified: (1) all had required approvals per discount threshold, (2) 20/20 Oracle price book matched approved price, (3) audit trail complete. Also tested 10 invoices against price book - all matched.',
            'operational_effectiveness_conclusion': 'Effective - Price change controls operating effectively with proper authorization and accurate system updates.'
        }
    ]

    for risk in risks:
        row_id = db.create_risk(
            risk_id=risk['risk_id'],
            risk=risk['risk'],
            control_id=risk['control_id'],
            control_owner=risk['control_owner'],
            status=risk['status']
        )
        conn = db._get_conn()
        conn.execute("""UPDATE risks SET
            audit_id = ?,
            design_effectiveness_testing = ?,
            design_effectiveness_conclusion = ?,
            operational_effectiveness_test = ?,
            operational_effectiveness_conclusion = ?
            WHERE id = ?""", (
            audit_id,
            risk.get('design_effectiveness_testing', ''),
            risk.get('design_effectiveness_conclusion', ''),
            risk.get('operational_effectiveness_test', ''),
            risk.get('operational_effectiveness_conclusion', ''),
            row_id
        ))
        conn.commit()
        conn.close()

    # Create test documents
    test_documents = [
        {
            'risk_id': 'REV-R001',
            'de_content': '''<h2>Design Effectiveness Testing - REV-R001</h2>
<h3>Control: Contract Review Checklist for Revenue Recognition</h3>
<p><strong>Test Objective:</strong> Verify the contract review process is designed to ensure ASC 606 compliant revenue recognition.</p>
<h3>Testing Procedures:</h3>
<ol>
<li>Obtained ASC 606 Revenue Recognition Policy</li>
<li>Reviewed Contract Review Checklist template</li>
<li>Verified Oracle system enforces checklist completion</li>
<li>Interviewed Revenue Recognition Manager</li>
</ol>
<h3>Checklist Elements Evaluated:</h3>
<table border="1" cellpadding="5">
<tr><th>Element</th><th>Requirement</th><th>Assessment</th></tr>
<tr><td>Performance Obligations</td><td>Identify all distinct obligations</td><td>Adequate</td></tr>
<tr><td>Transaction Price</td><td>Document variable consideration</td><td>Adequate</td></tr>
<tr><td>Allocation</td><td>Standalone selling price basis</td><td>Adequate</td></tr>
<tr><td>Timing</td><td>Point in time vs over time</td><td>Adequate</td></tr>
<tr><td>Evidence</td><td>Delivery/acceptance documentation</td><td>Adequate</td></tr>
</table>
<h3>Conclusion:</h3>
<p style="color: green;"><strong>EFFECTIVE</strong> - Contract review checklist comprehensively addresses ASC 606 requirements.</p>''',
            'oe_content': '''<h2>Operational Effectiveness Testing - REV-R001</h2>
<h3>Control: Contract Review Checklist for Revenue Recognition</h3>
<p><strong>Test Period:</strong> Q1-Q3 2025</p>
<p><strong>Population:</strong> 847 revenue transactions >$50,000</p>
<p><strong>Sample Size:</strong> 25 (using MUS sampling)</p>
<h3>Testing Results:</h3>
<table border="1" cellpadding="5">
<tr><th>Attribute</th><th>Expected</th><th>Tested</th><th>Exceptions</th></tr>
<tr><td>Checklist completed</td><td>100%</td><td>25/25</td><td style="color:green;">0</td></tr>
<tr><td>Performance obligations documented</td><td>100%</td><td>25/25</td><td style="color:green;">0</td></tr>
<tr><td>Delivery evidence on file</td><td>100%</td><td>23/25</td><td style="color:green;">0*</td></tr>
<tr><td>Manager approval</td><td>100%</td><td>25/25</td><td style="color:green;">0</td></tr>
</table>
<p><em>*2 items were subscription arrangements recognized over time - no point-in-time delivery evidence required.</em></p>
<h3>Conclusion:</h3>
<p style="color: green;"><strong>EFFECTIVE</strong> - Revenue recognition controls operating effectively.</p>'''
        },
        {
            'risk_id': 'REV-R004',
            'de_content': '''<h2>Design Effectiveness Testing - REV-R004</h2>
<h3>Control: Commission Calculation Review</h3>
<p><strong>Test Objective:</strong> Verify commission calculation controls are designed to ensure accuracy.</p>
<h3>System Configuration Review:</h3>
<ul>
<li>Xactly commission system integrated with Oracle revenue data</li>
<li>Commission rates configured per approved plan document</li>
<li>Tier thresholds: $0-100K (8%), $100K-500K (10%), $500K+ (12%)</li>
<li>Quota attainment multipliers: <80% (0.5x), 80-100% (1x), >100% (1.5x)</li>
</ul>
<h3>Review Process:</h3>
<ol>
<li>System generates monthly commission report</li>
<li>Sales Ops validates sample of calculations</li>
<li>Sales Ops Director reviews and signs off</li>
<li>Report submitted to Payroll by 5th business day</li>
</ol>
<h3>Conclusion:</h3>
<p style="color: green;"><strong>EFFECTIVE</strong> - Automated calculation with manual oversight appropriately designed.</p>''',
            'oe_content': '''<h2>Operational Effectiveness Testing - REV-R004</h2>
<h3>Control: Commission Calculation Review</h3>
<p><strong>Test Period:</strong> April - September 2025</p>
<h3>Monthly Sign-off Verification:</h3>
<table border="1" cellpadding="5">
<tr><th>Month</th><th>Total Commissions</th><th>Sign-off Date</th><th>Timely</th></tr>
<tr><td>April</td><td>$847,230</td><td>May 4</td><td style="color:green;">✓</td></tr>
<tr><td>May</td><td>$912,450</td><td>Jun 5</td><td style="color:green;">✓</td></tr>
<tr><td>June</td><td>$1,103,200</td><td>Jul 3</td><td style="color:green;">✓</td></tr>
<tr><td>July</td><td>$756,800</td><td>Aug 5</td><td style="color:green;">✓</td></tr>
<tr><td>August</td><td>$891,350</td><td>Sep 4</td><td style="color:green;">✓</td></tr>
<tr><td>September</td><td>$1,245,600</td><td>Oct 3</td><td style="color:green;">✓</td></tr>
</table>
<h3>Sample Deal Testing (5 per month = 30 total):</h3>
<p>Recalculated commission for 30 sampled deals against source revenue and plan rates.</p>
<p><strong>Result:</strong> 30/30 calculations accurate. No exceptions.</p>
<h3>Conclusion:</h3>
<p style="color: green;"><strong>EFFECTIVE</strong> - Commission controls operating effectively.</p>'''
        }
    ]

    for doc in test_documents:
        conn = db._get_conn()
        row = conn.execute("SELECT id FROM risks WHERE risk_id = ?", (doc['risk_id'],)).fetchone()
        if row:
            risk_db_id = row['id']
            conn.execute("""INSERT OR REPLACE INTO test_documents (risk_id, doc_type, content, audit_id)
                VALUES (?, 'de_testing', ?, ?)""", (risk_db_id, doc['de_content'], audit_id))
            conn.execute("""INSERT OR REPLACE INTO test_documents (risk_id, doc_type, content, audit_id)
                VALUES (?, 'oe_testing', ?, ?)""", (risk_db_id, doc['oe_content'], audit_id))
            conn.commit()
        conn.close()

    # Create issues
    issues = [
        {
            'title': 'Unbilled Revenue Aging',
            'description': '3 customer accounts have unbilled revenue >60 days totaling $135K. Root cause: delayed SOW approvals. Working with Sales to expedite.',
            'risk_id': 'REV-R003',
            'severity': 'Medium',
            'status': 'In Progress',
            'assigned_to': 'Billing Manager'
        }
    ]

    for issue in issues:
        issue_id = db.create_issue(
            title=issue['title'],
            description=issue['description'],
            risk_id=issue['risk_id'],
            severity=issue['severity'],
            status=issue['status'],
            assigned_to=issue['assigned_to']
        )
        conn = db._get_conn()
        row = conn.execute("SELECT id FROM issues WHERE issue_id = ?", (issue_id,)).fetchone()
        if row:
            conn.execute("UPDATE issues SET audit_id = ? WHERE id = ?", (audit_id, row['id']))
            conn.commit()
        conn.close()

    # Create tasks
    tasks = [
        {'title': 'Map revenue process', 'description': 'Document order-to-cash workflow', 'column_id': 'complete', 'priority': 'high'},
        {'title': 'Identify key contracts', 'description': 'Select sample of material contracts for review', 'column_id': 'complete', 'priority': 'high'},
        {'title': 'Test contract review checklist', 'description': 'Verify checklist completion for sample of 25 contracts', 'column_id': 'complete', 'priority': 'high'},
        {'title': 'Test credit memo processing', 'description': 'Sample 30 credit memos for SLA compliance', 'column_id': 'complete', 'priority': 'medium'},
        {'title': 'Review unbilled revenue', 'description': 'Analyze aging and follow-up procedures', 'column_id': 'fieldwork', 'priority': 'medium'},
        {'title': 'Test commission calculations', 'description': 'Recalculate sample of 30 deals', 'column_id': 'complete', 'priority': 'medium'},
        {'title': 'Verify pricing controls', 'description': 'Test price change approvals and system updates', 'column_id': 'complete', 'priority': 'medium'},
        {'title': 'Draft revenue cycle findings', 'description': 'Prepare summary of testing results', 'column_id': 'review', 'priority': 'high'},
    ]

    for task in tasks:
        task_id = db.create_task(
            title=task['title'],
            description=task['description'],
            column_id=task['column_id'],
            priority=task['priority']
        )
        conn = db._get_conn()
        conn.execute("UPDATE tasks SET audit_id = ? WHERE id = ?", (audit_id, task_id))
        conn.commit()
        conn.close()

    print(f"  Added {len(risks)} risks, {len(issues)} issues, {len(tasks)} tasks, {len(test_documents)} test documents to Revenue audit")


def seed_vendor_audit(db, audit_id):
    """Seed RACM for Vendor Management audit."""
    risks = [
        {
            'risk_id': 'VND-R001',
            'risk': 'Critical vendors not identified and monitored appropriately',
            'control_id': 'Annual vendor risk assessment with tiering based on criticality',
            'control_owner': 'Vendor Management Director',
            'status': 'Complete',
            'design_effectiveness_testing': 'Reviewed Vendor Risk Assessment Framework and tiering criteria. Framework includes: (1) annual assessment of all vendors >$50K spend, (2) tiering based on data access, business criticality, and spend, (3) Tier 1 (Critical) requires annual on-site assessment, (4) Tier 2 requires SOC report review, (5) Tier 3 requires questionnaire only. Assessment tracked in Archer GRC.',
            'design_effectiveness_conclusion': 'Effective - Risk-based tiering framework appropriately designed to focus oversight on highest-risk vendors.',
            'operational_effectiveness_test': 'Obtained 2025 vendor inventory (247 vendors). Verified tiering: 12 Tier 1, 45 Tier 2, 190 Tier 3. Tested Tier 1 vendors: 12/12 had completed on-site assessments. Tested sample of 15 Tier 2 vendors: 15/15 had SOC 2 reports on file and reviewed. Verified new vendor onboarding includes risk assessment before contract execution.',
            'operational_effectiveness_conclusion': 'Effective - Vendor risk assessment process operating effectively with appropriate monitoring based on tier.'
        },
        {
            'risk_id': 'VND-R002',
            'risk': 'Vendor contracts may not include required security and compliance terms',
            'control_id': 'Contract template with mandatory security addendum for data-handling vendors',
            'control_owner': 'Legal Counsel',
            'status': 'Complete',
            'design_effectiveness_testing': 'Reviewed Master Services Agreement template and Data Processing Addendum (DPA). Template includes: (1) security requirements per data classification, (2) right to audit clause, (3) breach notification within 24 hours, (4) data return/destruction at termination, (5) insurance minimums, (6) indemnification. DPA includes GDPR/CCPA compliance terms.',
            'design_effectiveness_conclusion': 'Effective - Contract templates comprehensively address security and compliance requirements.',
            'operational_effectiveness_test': 'Tested sample of 20 data-handling vendor contracts executed in 2025. Verified: (1) 20/20 used approved template, (2) 20/20 included DPA, (3) 18/20 had no material deviations from standard terms. 2 contracts had negotiated modifications - both approved by Legal and documented in Archer with risk acceptance.',
            'operational_effectiveness_conclusion': 'Effective - Contract controls operating effectively with proper use of templates and documented exceptions.'
        },
        {
            'risk_id': 'VND-R003',
            'risk': 'Vendor performance issues not identified timely',
            'control_id': 'Quarterly business review with SLA tracking for critical vendors',
            'control_owner': 'Vendor Management Director',
            'status': 'In Progress',
            'design_effectiveness_testing': 'Reviewed Vendor Performance Management process. Tier 1 vendors have: (1) defined SLAs in contract, (2) monthly SLA reporting from vendor, (3) quarterly business review meetings, (4) annual performance scorecard. SLA breaches trigger escalation process. Performance issues tracked in ServiceNow.',
            'design_effectiveness_conclusion': 'Effective - Performance management process designed to identify and address vendor issues timely.',
            'operational_effectiveness_test': 'Testing in progress. Reviewed Q1-Q3 quarterly business review documentation for 12 Tier 1 vendors. 11/12 had complete QBR packages with SLA metrics. 1 vendor (cloud infrastructure) missed Q2 QBR due to scheduling conflict - conducted in July. Identified 3 SLA breaches - all had documented remediation plans.',
            'operational_effectiveness_conclusion': ''
        }
    ]

    for risk in risks:
        row_id = db.create_risk(
            risk_id=risk['risk_id'],
            risk=risk['risk'],
            control_id=risk['control_id'],
            control_owner=risk['control_owner'],
            status=risk['status']
        )
        conn = db._get_conn()
        conn.execute("""UPDATE risks SET
            audit_id = ?,
            design_effectiveness_testing = ?,
            design_effectiveness_conclusion = ?,
            operational_effectiveness_test = ?,
            operational_effectiveness_conclusion = ?
            WHERE id = ?""", (
            audit_id,
            risk.get('design_effectiveness_testing', ''),
            risk.get('design_effectiveness_conclusion', ''),
            risk.get('operational_effectiveness_test', ''),
            risk.get('operational_effectiveness_conclusion', ''),
            row_id
        ))
        conn.commit()
        conn.close()

    # Create test documents
    test_documents = [
        {
            'risk_id': 'VND-R001',
            'de_content': '''<h2>Design Effectiveness Testing - VND-R001</h2>
<h3>Control: Annual Vendor Risk Assessment</h3>
<p><strong>Test Objective:</strong> Verify vendor risk assessment process is designed to identify and appropriately monitor critical vendors.</p>
<h3>Tiering Criteria Reviewed:</h3>
<table border="1" cellpadding="5">
<tr><th>Tier</th><th>Criteria</th><th>Monitoring Requirements</th></tr>
<tr><td>Tier 1 (Critical)</td><td>PII/PHI access OR >$1M spend OR single-source</td><td>Annual on-site assessment, quarterly reviews</td></tr>
<tr><td>Tier 2 (High)</td><td>Confidential data OR >$250K spend</td><td>Annual SOC 2 review, semi-annual check-in</td></tr>
<tr><td>Tier 3 (Standard)</td><td>All others >$50K</td><td>Annual questionnaire</td></tr>
</table>
<h3>Assessment Components:</h3>
<ul>
<li>Financial stability (D&B rating, public filings)</li>
<li>Security posture (SOC reports, penetration tests)</li>
<li>Business continuity capabilities</li>
<li>Regulatory compliance status</li>
<li>Concentration risk evaluation</li>
</ul>
<h3>Conclusion:</h3>
<p style="color: green;"><strong>EFFECTIVE</strong> - Risk-based framework appropriately designed for vendor oversight.</p>''',
            'oe_content': '''<h2>Operational Effectiveness Testing - VND-R001</h2>
<h3>Control: Annual Vendor Risk Assessment</h3>
<p><strong>Test Period:</strong> 2025 vendor assessments</p>
<h3>Vendor Population:</h3>
<table border="1" cellpadding="5">
<tr><th>Tier</th><th>Count</th><th>Tested</th><th>Compliance</th></tr>
<tr><td>Tier 1</td><td>12</td><td>12 (100%)</td><td style="color:green;">12/12</td></tr>
<tr><td>Tier 2</td><td>45</td><td>15 (33%)</td><td style="color:green;">15/15</td></tr>
<tr><td>Tier 3</td><td>190</td><td>20 (11%)</td><td style="color:green;">20/20</td></tr>
</table>
<h3>Tier 1 Assessment Details:</h3>
<table border="1" cellpadding="5">
<tr><th>Vendor</th><th>Category</th><th>On-site Date</th><th>Rating</th></tr>
<tr><td>CloudCorp AWS</td><td>Infrastructure</td><td>Feb 2025</td><td>Satisfactory</td></tr>
<tr><td>PaymentPro</td><td>Payment Processing</td><td>Mar 2025</td><td>Satisfactory</td></tr>
<tr><td>DataSecure</td><td>Data Center</td><td>Jan 2025</td><td>Satisfactory</td></tr>
<tr><td>HRCloud</td><td>HRIS</td><td>Apr 2025</td><td>Needs Improvement</td></tr>
</table>
<p><em>HRCloud remediation plan tracked - 2 of 3 findings closed as of Oct 2025.</em></p>
<h3>Conclusion:</h3>
<p style="color: green;"><strong>EFFECTIVE</strong> - Vendor assessments completed per requirements.</p>'''
        },
        {
            'risk_id': 'VND-R002',
            'de_content': '''<h2>Design Effectiveness Testing - VND-R002</h2>
<h3>Control: Contract Security Terms</h3>
<p><strong>Test Objective:</strong> Verify contract templates include required security and compliance terms.</p>
<h3>MSA Template Review:</h3>
<table border="1" cellpadding="5">
<tr><th>Clause</th><th>Requirement</th><th>Present</th></tr>
<tr><td>Security Standards</td><td>SOC 2 Type II or equivalent</td><td style="color:green;">✓</td></tr>
<tr><td>Audit Rights</td><td>Right to audit with 30-day notice</td><td style="color:green;">✓</td></tr>
<tr><td>Breach Notification</td><td>24-hour notification requirement</td><td style="color:green;">✓</td></tr>
<tr><td>Data Handling</td><td>Encryption, access controls</td><td style="color:green;">✓</td></tr>
<tr><td>Termination</td><td>Data return/destruction</td><td style="color:green;">✓</td></tr>
<tr><td>Insurance</td><td>Cyber liability minimums</td><td style="color:green;">✓</td></tr>
</table>
<h3>Data Processing Addendum:</h3>
<ul>
<li>GDPR Article 28 compliant processor terms</li>
<li>CCPA service provider certification</li>
<li>Sub-processor notification requirements</li>
<li>Cross-border transfer mechanisms (SCCs)</li>
</ul>
<h3>Conclusion:</h3>
<p style="color: green;"><strong>EFFECTIVE</strong> - Contract templates comprehensive.</p>''',
            'oe_content': '''<h2>Operational Effectiveness Testing - VND-R002</h2>
<h3>Control: Contract Security Terms</h3>
<p><strong>Test Period:</strong> Contracts executed in 2025</p>
<p><strong>Population:</strong> 67 data-handling vendor contracts</p>
<p><strong>Sample:</strong> 20 contracts</p>
<h3>Testing Results:</h3>
<table border="1" cellpadding="5">
<tr><th>Attribute</th><th>Expected</th><th>Result</th></tr>
<tr><td>Used approved MSA template</td><td>100%</td><td style="color:green;">20/20</td></tr>
<tr><td>DPA included</td><td>100%</td><td style="color:green;">20/20</td></tr>
<tr><td>No material deviations</td><td>100%</td><td style="color:orange;">18/20</td></tr>
<tr><td>Deviations approved by Legal</td><td>100%</td><td style="color:green;">2/2</td></tr>
</table>
<h3>Deviation Details:</h3>
<ol>
<li><strong>Vendor A:</strong> Modified breach notification to 48 hours (vendor limitation). Risk accepted by CISO - documented in Archer.</li>
<li><strong>Vendor B:</strong> Reduced audit rights to annual only. Compensated by SOC 2 Type II report requirement - approved by Legal.</li>
</ol>
<h3>Conclusion:</h3>
<p style="color: green;"><strong>EFFECTIVE</strong> - Contract controls operating with appropriate exception handling.</p>'''
        }
    ]

    for doc in test_documents:
        conn = db._get_conn()
        row = conn.execute("SELECT id FROM risks WHERE risk_id = ?", (doc['risk_id'],)).fetchone()
        if row:
            risk_db_id = row['id']
            conn.execute("""INSERT OR REPLACE INTO test_documents (risk_id, doc_type, content, audit_id)
                VALUES (?, 'de_testing', ?, ?)""", (risk_db_id, doc['de_content'], audit_id))
            conn.execute("""INSERT OR REPLACE INTO test_documents (risk_id, doc_type, content, audit_id)
                VALUES (?, 'oe_testing', ?, ?)""", (risk_db_id, doc['oe_content'], audit_id))
            conn.commit()
        conn.close()

    # Create issues
    issues = [
        {
            'title': 'HRCloud Vendor Remediation Pending',
            'description': 'On-site assessment identified 3 findings: (1) Missing MFA for admin access - CLOSED, (2) Backup encryption gap - CLOSED, (3) Incident response plan outdated - IN PROGRESS. Target closure: Nov 2025.',
            'risk_id': 'VND-R001',
            'severity': 'Medium',
            'status': 'In Progress',
            'assigned_to': 'Vendor Management Director'
        },
        {
            'title': 'Q2 QBR Scheduling Miss',
            'description': 'CloudCorp AWS Q2 quarterly business review was delayed by 3 weeks due to vendor availability. Implemented calendar holds for all Tier 1 QBRs 60 days in advance.',
            'risk_id': 'VND-R003',
            'severity': 'Low',
            'status': 'Closed',
            'assigned_to': 'Vendor Management Director'
        }
    ]

    for issue in issues:
        issue_id = db.create_issue(
            title=issue['title'],
            description=issue['description'],
            risk_id=issue['risk_id'],
            severity=issue['severity'],
            status=issue['status'],
            assigned_to=issue['assigned_to']
        )
        conn = db._get_conn()
        row = conn.execute("SELECT id FROM issues WHERE issue_id = ?", (issue_id,)).fetchone()
        if row:
            conn.execute("UPDATE issues SET audit_id = ? WHERE id = ?", (audit_id, row['id']))
            conn.commit()
        conn.close()

    # Create tasks
    tasks = [
        {'title': 'Obtain vendor inventory', 'description': 'Extract complete vendor list from procurement system', 'column_id': 'complete', 'priority': 'high'},
        {'title': 'Verify vendor tiering', 'description': 'Confirm tier assignments match criteria', 'column_id': 'complete', 'priority': 'high'},
        {'title': 'Test Tier 1 assessments', 'description': 'Review on-site assessment documentation for all 12 critical vendors', 'column_id': 'complete', 'priority': 'high'},
        {'title': 'Sample Tier 2 SOC reviews', 'description': 'Test 15 Tier 2 vendors for SOC report review', 'column_id': 'complete', 'priority': 'medium'},
        {'title': 'Review contract templates', 'description': 'Verify MSA and DPA include required terms', 'column_id': 'complete', 'priority': 'medium'},
        {'title': 'Test contract compliance', 'description': 'Sample 20 contracts for template usage', 'column_id': 'complete', 'priority': 'medium'},
        {'title': 'Review QBR documentation', 'description': 'Verify quarterly business reviews for Tier 1 vendors', 'column_id': 'fieldwork', 'priority': 'medium'},
        {'title': 'Follow up on vendor findings', 'description': 'Track remediation status for identified issues', 'column_id': 'fieldwork', 'priority': 'high'},
        {'title': 'Draft vendor management findings', 'description': 'Prepare audit findings summary', 'column_id': 'planning', 'priority': 'high'},
    ]

    for task in tasks:
        task_id = db.create_task(
            title=task['title'],
            description=task['description'],
            column_id=task['column_id'],
            priority=task['priority']
        )
        conn = db._get_conn()
        conn.execute("UPDATE tasks SET audit_id = ? WHERE id = ?", (audit_id, task_id))
        conn.commit()
        conn.close()

    print(f"  Added {len(risks)} risks, {len(issues)} issues, {len(tasks)} tasks, {len(test_documents)} test documents to Vendor audit")


def seed_cyber_audit(db, audit_id):
    """Seed RACM for Cybersecurity audit."""
    risks = [
        {
            'risk_id': 'CYB-R001',
            'risk': 'Phishing attacks may compromise user credentials',
            'control_id': 'Mandatory security awareness training with quarterly phishing simulations',
            'control_owner': 'CISO',
            'status': 'Complete',
            'design_effectiveness_testing': 'Reviewed Security Awareness Training Program documentation. Confirmed: (1) Annual mandatory training for all employees, (2) Quarterly phishing simulations conducted by KnowBe4, (3) Repeat clickers receive additional training, (4) Metrics reported to CISO monthly. Training content covers phishing, social engineering, password security, and data handling.',
            'design_effectiveness_conclusion': 'Effective - Training program comprehensively designed to reduce human-factor security risks.',
            'operational_effectiveness_test': 'Obtained training completion reports for 2025. 98.5% completion rate (1,247/1,266 employees). Reviewed Q1-Q4 phishing simulation results: Q1: 12% click rate, Q2: 8% click rate, Q3: 5% click rate, Q4: 4% click rate. Verified 23 repeat clickers received remedial training within 48 hours.',
            'operational_effectiveness_conclusion': 'Effective - Training program operating effectively with measurable improvement in phishing resistance.'
        },
        {
            'risk_id': 'CYB-R002',
            'risk': 'Unpatched vulnerabilities in internet-facing systems',
            'control_id': 'Monthly vulnerability scanning with 30-day critical patch SLA',
            'control_owner': 'Security Operations Manager',
            'status': 'In Progress',
            'design_effectiveness_testing': 'Reviewed Vulnerability Management Policy and Qualys scanner configuration. Policy requires: (1) Weekly scans of external assets, (2) Monthly scans of internal assets, (3) Critical vulnerabilities patched within 30 days, (4) High within 60 days, (5) Medium within 90 days. Scan results feed into ServiceNow for tracking.',
            'design_effectiveness_conclusion': 'Effective - Vulnerability management process appropriately designed with risk-based remediation timelines.',
            'operational_effectiveness_test': 'Obtained vulnerability scan reports for Jan-Sep 2025. Tested sample of 30 critical vulnerabilities identified. 27/30 (90%) remediated within 30-day SLA. 3 exceptions: 2 required application changes (remediated in 45 days with documented exception), 1 legacy system pending decommission (compensating control in place).',
            'operational_effectiveness_conclusion': 'Effective with exceptions - Minor SLA misses documented with valid business justification and compensating controls.'
        },
        {
            'risk_id': 'CYB-R003',
            'risk': 'Security incidents not detected or responded to timely',
            'control_id': 'SIEM monitoring with 24/7 SOC coverage and incident response playbooks',
            'control_owner': 'Security Operations Manager',
            'status': 'Complete',
            'design_effectiveness_testing': 'Reviewed Splunk SIEM configuration and SOC procedures. Confirmed: (1) Log sources include firewalls, endpoints, cloud, AD, (2) 847 correlation rules active, (3) 24/7 SOC staffing via MSSP, (4) 15-minute SLA for P1 alerts, (5) Documented playbooks for top 20 incident types. Tested alert routing to SOC.',
            'design_effectiveness_conclusion': 'Effective - SIEM and SOC capabilities appropriately designed to detect and respond to security incidents.',
            'operational_effectiveness_test': 'Reviewed SOC metrics for 2025: 47,832 alerts generated, 312 escalated as potential incidents, 28 confirmed security incidents. Tested sample of 15 incidents: all had documented timelines, root cause analysis, and remediation. Average detection-to-containment: 2.3 hours for P1, 8.1 hours for P2. Verified tabletop exercises conducted quarterly.',
            'operational_effectiveness_conclusion': 'Effective - SOC demonstrating strong detection and response capabilities with documented incident handling.'
        },
        {
            'risk_id': 'CYB-R004',
            'risk': 'Sensitive data exposed through misconfigured cloud resources',
            'control_id': 'Cloud security posture management (CSPM) with automated remediation',
            'control_owner': 'Cloud Security Architect',
            'status': 'In Progress',
            'design_effectiveness_testing': 'Reviewed Wiz CSPM implementation. Platform monitors AWS, Azure, and GCP environments. 156 security policies enforced covering: public S3 buckets, unencrypted databases, overly permissive IAM, exposed secrets. Auto-remediation enabled for 12 critical misconfigurations. Alerts integrate with Slack and PagerDuty.',
            'design_effectiveness_conclusion': 'Effective - CSPM solution comprehensively designed to identify and remediate cloud misconfigurations.',
            'operational_effectiveness_test': 'Testing in progress - reviewing CSPM findings and remediation timelines for Q3-Q4 2025.',
            'operational_effectiveness_conclusion': ''
        },
        {
            'risk_id': 'CYB-R005',
            'risk': 'Ransomware attack could disrupt business operations',
            'control_id': 'Endpoint detection and response (EDR) with network segmentation',
            'control_owner': 'CISO',
            'status': 'Complete',
            'design_effectiveness_testing': 'Reviewed CrowdStrike Falcon EDR deployment. Confirmed: (1) Agent deployed on 100% of endpoints (3,847 devices), (2) Real-time behavioral analysis enabled, (3) Automated isolation for ransomware indicators, (4) Network segmented into 12 security zones with firewall rules. Tested sample alert to verify SOC notification.',
            'design_effectiveness_conclusion': 'Effective - EDR and network segmentation provide defense-in-depth against ransomware.',
            'operational_effectiveness_test': 'Reviewed EDR telemetry for 2025. 0 ransomware incidents detected/blocked. Verified 3 simulated ransomware tests (red team exercises) were detected and contained within 5 minutes. Confirmed backup restoration test completed successfully in April 2025 (RTO: 4 hours achieved vs. 8 hour target). Network segmentation rules reviewed - no unauthorized cross-zone traffic detected.',
            'operational_effectiveness_conclusion': 'Effective - Controls operating effectively with demonstrated detection and recovery capabilities.'
        },
        {
            'risk_id': 'CYB-R006',
            'risk': 'Third-party integrations may introduce security vulnerabilities',
            'control_id': 'API security gateway with authentication and rate limiting',
            'control_owner': 'Application Security Manager',
            'status': 'In Progress',
            'design_effectiveness_testing': 'Reviewed Kong API Gateway configuration. All external APIs route through gateway with: (1) OAuth 2.0 / API key authentication required, (2) Rate limiting: 1000 req/min per client, (3) Request/response validation against OpenAPI specs, (4) WAF rules for OWASP Top 10, (5) Logging of all API calls to SIEM.',
            'design_effectiveness_conclusion': 'Effective - API gateway provides comprehensive security controls for third-party integrations.',
            'operational_effectiveness_test': 'Obtained API gateway logs for Q3 2025. Tested sample of 25 API integrations: all authenticated correctly, rate limits enforced. Reviewed 3 blocked attack attempts (SQL injection, XXE). Verified API inventory matches gateway configuration (47 active integrations). Pending: review of Q4 penetration test results.',
            'operational_effectiveness_conclusion': 'Testing in progress - awaiting Q4 penetration test results.'
        }
    ]

    for risk in risks:
        row_id = db.create_risk(
            risk_id=risk['risk_id'],
            risk=risk['risk'],
            control_id=risk['control_id'],
            control_owner=risk['control_owner'],
            status=risk['status']
        )
        conn = db._get_conn()
        conn.execute("""UPDATE risks SET
            audit_id = ?,
            design_effectiveness_testing = ?,
            design_effectiveness_conclusion = ?,
            operational_effectiveness_test = ?,
            operational_effectiveness_conclusion = ?
            WHERE id = ?""", (
            audit_id,
            risk.get('design_effectiveness_testing', ''),
            risk.get('design_effectiveness_conclusion', ''),
            risk.get('operational_effectiveness_test', ''),
            risk.get('operational_effectiveness_conclusion', ''),
            row_id
        ))
        conn.commit()
        conn.close()

    # Add test documents for completed controls
    test_documents = [
        {
            'risk_id': 'CYB-R001',
            'de_content': '''<h2>Design Effectiveness Testing - CYB-R001</h2>
<h3>Control: Security Awareness Training Program</h3>
<p><strong>Test Objective:</strong> Verify the training program is appropriately designed to reduce phishing and social engineering risks.</p>
<h3>Testing Procedures:</h3>
<ol>
<li>Obtained Security Awareness Training Policy v3.1</li>
<li>Reviewed KnowBe4 platform configuration and content library</li>
<li>Interviewed CISO regarding program objectives and metrics</li>
<li>Reviewed sample training modules for completeness</li>
</ol>
<h3>Evidence Obtained:</h3>
<ul>
<li>Security Awareness Policy (Ref: WP-CYB-001-A)</li>
<li>KnowBe4 configuration screenshots</li>
<li>Sample phishing simulation templates</li>
<li>Training completion workflow documentation</li>
</ul>
<h3>Key Design Elements:</h3>
<table border="1" cellpadding="5">
<tr><th>Element</th><th>Design</th><th>Assessment</th></tr>
<tr><td>Training Frequency</td><td>Annual mandatory + quarterly refreshers</td><td>Adequate</td></tr>
<tr><td>Phishing Simulations</td><td>Quarterly via KnowBe4</td><td>Adequate</td></tr>
<tr><td>Repeat Clicker Handling</td><td>Additional training within 48 hours</td><td>Adequate</td></tr>
<tr><td>Coverage</td><td>All employees including contractors</td><td>Adequate</td></tr>
<tr><td>Content</td><td>Phishing, social engineering, passwords, data handling</td><td>Comprehensive</td></tr>
</table>
<h3>Conclusion:</h3>
<p style="color: green;"><strong>EFFECTIVE</strong> - Training program comprehensively designed to address human-factor security risks.</p>''',
            'oe_content': '''<h2>Operational Effectiveness Testing - CYB-R001</h2>
<h3>Control: Security Awareness Training Program</h3>
<p><strong>Test Period:</strong> January 2025 - December 2025</p>
<h3>Testing Procedures:</h3>
<ol>
<li>Obtained annual training completion reports from KnowBe4</li>
<li>Reviewed quarterly phishing simulation results</li>
<li>Tested sample of repeat clickers for remedial training</li>
<li>Verified new hire training completion within 30 days</li>
</ol>
<h3>Training Completion Results:</h3>
<table border="1" cellpadding="5">
<tr><th>Metric</th><th>Target</th><th>Actual</th><th>Result</th></tr>
<tr><td>Annual Training Completion</td><td>95%</td><td>98.5% (1,247/1,266)</td><td style="color:green;">Pass</td></tr>
<tr><td>New Hire Training (30 days)</td><td>100%</td><td>100% (127/127)</td><td style="color:green;">Pass</td></tr>
<tr><td>Repeat Clicker Remediation</td><td>48 hours</td><td>100% within SLA</td><td style="color:green;">Pass</td></tr>
</table>
<h3>Phishing Simulation Trend:</h3>
<table border="1" cellpadding="5">
<tr><th>Quarter</th><th>Emails Sent</th><th>Clicks</th><th>Click Rate</th><th>Trend</th></tr>
<tr><td>Q1 2025</td><td>1,266</td><td>152</td><td>12%</td><td>Baseline</td></tr>
<tr><td>Q2 2025</td><td>1,271</td><td>102</td><td>8%</td><td style="color:green;">↓ Improving</td></tr>
<tr><td>Q3 2025</td><td>1,259</td><td>63</td><td>5%</td><td style="color:green;">↓ Improving</td></tr>
<tr><td>Q4 2025</td><td>1,266</td><td>51</td><td>4%</td><td style="color:green;">↓ Improving</td></tr>
</table>
<h3>Conclusion:</h3>
<p style="color: green;"><strong>EFFECTIVE</strong> - Training program operating effectively with measurable improvement in security awareness.</p>'''
        },
        {
            'risk_id': 'CYB-R003',
            'de_content': '''<h2>Design Effectiveness Testing - CYB-R003</h2>
<h3>Control: SIEM Monitoring with 24/7 SOC</h3>
<p><strong>Test Objective:</strong> Verify SIEM and SOC are designed to detect and respond to security incidents timely.</p>
<h3>Testing Procedures:</h3>
<ol>
<li>Reviewed Splunk SIEM architecture and log sources</li>
<li>Examined correlation rules and alert thresholds</li>
<li>Reviewed SOC procedures and staffing model</li>
<li>Tested sample alert escalation to SOC</li>
</ol>
<h3>Log Source Coverage:</h3>
<table border="1" cellpadding="5">
<tr><th>Source Type</th><th>Systems</th><th>EPS</th></tr>
<tr><td>Firewalls</td><td>Palo Alto (12 devices)</td><td>15,000</td></tr>
<tr><td>Endpoints</td><td>CrowdStrike (3,847 agents)</td><td>8,500</td></tr>
<tr><td>Cloud</td><td>AWS CloudTrail, Azure AD</td><td>12,000</td></tr>
<tr><td>Identity</td><td>Active Directory, Okta</td><td>3,200</td></tr>
<tr><td>Applications</td><td>Critical business apps (15)</td><td>5,800</td></tr>
</table>
<h3>SOC Capabilities:</h3>
<ul>
<li>24/7 coverage via Arctic Wolf MSSP</li>
<li>15-minute SLA for P1 alert triage</li>
<li>20 documented incident response playbooks</li>
<li>Quarterly tabletop exercises</li>
</ul>
<h3>Conclusion:</h3>
<p style="color: green;"><strong>EFFECTIVE</strong> - SIEM and SOC appropriately designed for threat detection and incident response.</p>''',
            'oe_content': '''<h2>Operational Effectiveness Testing - CYB-R003</h2>
<h3>Control: SIEM Monitoring with 24/7 SOC</h3>
<p><strong>Test Period:</strong> January 2025 - September 2025</p>
<h3>SOC Metrics Summary:</h3>
<table border="1" cellpadding="5">
<tr><th>Metric</th><th>Value</th></tr>
<tr><td>Total Alerts Generated</td><td>47,832</td></tr>
<tr><td>Alerts Escalated</td><td>312 (0.65%)</td></tr>
<tr><td>Confirmed Incidents</td><td>28</td></tr>
<tr><td>False Positive Rate</td><td>91%</td></tr>
</table>
<h3>Incident Response Testing:</h3>
<p>Selected sample of 15 confirmed incidents for detailed review:</p>
<table border="1" cellpadding="5">
<tr><th>Incident</th><th>Type</th><th>Detection</th><th>Containment</th><th>Resolution</th></tr>
<tr><td>INC-2025-003</td><td>Malware</td><td>8 min</td><td>45 min</td><td>4 hours</td></tr>
<tr><td>INC-2025-007</td><td>Phishing</td><td>12 min</td><td>30 min</td><td>2 hours</td></tr>
<tr><td>INC-2025-012</td><td>Brute Force</td><td>5 min</td><td>15 min</td><td>1 hour</td></tr>
<tr><td>INC-2025-019</td><td>Data Exfil Attempt</td><td>18 min</td><td>2 hours</td><td>8 hours</td></tr>
<tr><td>INC-2025-024</td><td>Insider Threat</td><td>4 hours</td><td>6 hours</td><td>3 days</td></tr>
</table>
<p><em>All 15 sampled incidents had documented root cause analysis and remediation actions.</em></p>
<h3>Average Response Times:</h3>
<ul>
<li>P1 Incidents: Detection to Containment = 2.3 hours (Target: 4 hours) ✓</li>
<li>P2 Incidents: Detection to Containment = 8.1 hours (Target: 24 hours) ✓</li>
</ul>
<h3>Conclusion:</h3>
<p style="color: green;"><strong>EFFECTIVE</strong> - SOC demonstrating strong detection and response capabilities.</p>'''
        }
    ]

    # Insert test documents
    for doc in test_documents:
        conn = db._get_conn()
        row = conn.execute("SELECT id FROM risks WHERE risk_id = ?", (doc['risk_id'],)).fetchone()
        if row:
            risk_db_id = row['id']
            conn.execute("""INSERT OR REPLACE INTO test_documents (risk_id, doc_type, content, audit_id)
                VALUES (?, 'de_testing', ?, ?)""", (risk_db_id, doc['de_content'], audit_id))
            conn.execute("""INSERT OR REPLACE INTO test_documents (risk_id, doc_type, content, audit_id)
                VALUES (?, 'oe_testing', ?, ?)""", (risk_db_id, doc['oe_content'], audit_id))
            conn.commit()
        conn.close()

    # Create issues
    issues = [
        {
            'title': 'Vulnerability Patch SLA Exceptions',
            'description': '3 critical vulnerabilities exceeded 30-day SLA. Root causes: 2 required application changes, 1 legacy system. All have documented remediation plans or compensating controls.',
            'risk_id': 'CYB-R002',
            'severity': 'Medium',
            'status': 'In Progress',
            'assigned_to': 'Security Operations Manager'
        },
        {
            'title': 'CSPM Auto-Remediation Gap',
            'description': 'Auto-remediation only enabled for 12 of 156 security policies. Recommend expanding to additional high-risk misconfigurations.',
            'risk_id': 'CYB-R004',
            'severity': 'Low',
            'status': 'Open',
            'assigned_to': 'Cloud Security Architect'
        },
        {
            'title': 'API Inventory Mismatch',
            'description': 'Initial API inventory showed 52 integrations but gateway only had 47 configured. 5 legacy APIs identified operating outside gateway - migration plan in progress.',
            'risk_id': 'CYB-R006',
            'severity': 'Medium',
            'status': 'In Progress',
            'assigned_to': 'Application Security Manager'
        }
    ]

    for issue in issues:
        issue_id = db.create_issue(
            title=issue['title'],
            description=issue['description'],
            risk_id=issue['risk_id'],
            severity=issue['severity'],
            status=issue['status'],
            assigned_to=issue['assigned_to']
        )
        conn = db._get_conn()
        row = conn.execute("SELECT id FROM issues WHERE issue_id = ?", (issue_id,)).fetchone()
        if row:
            conn.execute("UPDATE issues SET audit_id = ? WHERE id = ?", (audit_id, row['id']))
            conn.commit()
        conn.close()

    # Create tasks
    tasks = [
        {'title': 'Review security awareness program', 'description': 'Obtain KnowBe4 training and phishing simulation data', 'column_id': 'complete', 'priority': 'high'},
        {'title': 'Test vulnerability management', 'description': 'Sample 30 critical vulnerabilities for remediation SLA', 'column_id': 'complete', 'priority': 'high'},
        {'title': 'Evaluate SIEM coverage', 'description': 'Review log sources and correlation rules', 'column_id': 'complete', 'priority': 'high'},
        {'title': 'Test incident response', 'description': 'Review sample of 15 security incidents', 'column_id': 'complete', 'priority': 'high'},
        {'title': 'Assess CSPM implementation', 'description': 'Review Wiz configuration and findings remediation', 'column_id': 'fieldwork', 'priority': 'medium'},
        {'title': 'Test EDR deployment', 'description': 'Verify 100% endpoint coverage and detection capabilities', 'column_id': 'complete', 'priority': 'high'},
        {'title': 'Review API security controls', 'description': 'Test API gateway authentication and rate limiting', 'column_id': 'fieldwork', 'priority': 'medium'},
        {'title': 'Verify backup/recovery', 'description': 'Review backup restoration test results', 'column_id': 'complete', 'priority': 'medium'},
        {'title': 'Review red team results', 'description': 'Analyze findings from annual penetration test', 'column_id': 'review', 'priority': 'high'},
        {'title': 'Draft cybersecurity findings', 'description': 'Prepare audit report with identified gaps', 'column_id': 'planning', 'priority': 'high'},
    ]

    for task in tasks:
        task_id = db.create_task(
            title=task['title'],
            description=task['description'],
            column_id=task['column_id'],
            priority=task['priority']
        )
        conn = db._get_conn()
        conn.execute("UPDATE tasks SET audit_id = ? WHERE id = ?", (audit_id, task_id))
        conn.commit()
        conn.close()

    print(f"  Added {len(risks)} risks, {len(issues)} issues, {len(tasks)} tasks, {len(test_documents)} test documents to Cybersecurity audit")


def seed_flowcharts(db, audit_id, audit_type):
    """Create sample process flowcharts for an audit."""
    flowcharts = []

    if audit_type == 'sox':
        # Financial Close Process Flowchart - links to SOX-R001 (Financial statement errors)
        flowcharts.append({
            'name': f'financial-close-process-{audit_id}',
            'risk_id': 'SOX-R001',
            'data': {
                "drawflow": {
                    "Home": {
                        "data": {
                            "1": {
                                "id": 1,
                                "name": "start",
                                "data": {"name": "Month End Close Initiated"},
                                "class": "start",
                                "html": "Month End Close Initiated",
                                "typenode": "vue",
                                "inputs": {},
                                "outputs": {"output_1": {"connections": [{"node": "2", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 100
                            },
                            "2": {
                                "id": 2,
                                "name": "process",
                                "data": {"name": "Sub-ledger Close"},
                                "class": "process",
                                "html": "Sub-ledger Close\n(AR, AP, FA, Inventory)",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "1", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "3", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 200
                            },
                            "3": {
                                "id": 3,
                                "name": "process",
                                "data": {"name": "Journal Entries"},
                                "class": "process",
                                "html": "Post Adjusting\nJournal Entries",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "2", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "4", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 300
                            },
                            "4": {
                                "id": 4,
                                "name": "decision",
                                "data": {"name": "JE > $10K?"},
                                "class": "decision",
                                "html": "JE Amount\n> $10,000?",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "3", "input": "output_1"}]}},
                                "outputs": {
                                    "output_1": {"connections": [{"node": "5", "output": "input_1"}]},
                                    "output_2": {"connections": [{"node": "6", "output": "input_1"}]}
                                },
                                "pos_x": 100,
                                "pos_y": 400
                            },
                            "5": {
                                "id": 5,
                                "name": "process",
                                "data": {"name": "Dual Approval"},
                                "class": "process",
                                "html": "Obtain Dual Approval\n(Controller + CFO)",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "4", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "6", "output": "input_1"}]}},
                                "pos_x": 300,
                                "pos_y": 400
                            },
                            "6": {
                                "id": 6,
                                "name": "process",
                                "data": {"name": "Reconciliations"},
                                "class": "process",
                                "html": "Prepare Account\nReconciliations",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "4", "input": "output_2"}, {"node": "5", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "7", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 500
                            },
                            "7": {
                                "id": 7,
                                "name": "process",
                                "data": {"name": "Variance Analysis"},
                                "class": "process",
                                "html": "Perform Variance\nAnalysis (>10%)",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "6", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "8", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 600
                            },
                            "8": {
                                "id": 8,
                                "name": "process",
                                "data": {"name": "CFO Review"},
                                "class": "process",
                                "html": "CFO Reviews\nClose Package",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "7", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "9", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 700
                            },
                            "9": {
                                "id": 9,
                                "name": "end",
                                "data": {"name": "Close Complete"},
                                "class": "end",
                                "html": "Month End Close\nComplete",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "8", "input": "output_1"}]}},
                                "outputs": {},
                                "pos_x": 100,
                                "pos_y": 800
                            }
                        }
                    }
                }
            }
        })

        # Revenue Recognition Process - links to SOX-R003 (Revenue period errors)
        flowcharts.append({
            'name': f'revenue-recognition-{audit_id}',
            'risk_id': 'SOX-R003',
            'data': {
                "drawflow": {
                    "Home": {
                        "data": {
                            "1": {
                                "id": 1,
                                "name": "start",
                                "data": {"name": "Customer Order Received"},
                                "class": "start",
                                "html": "Customer Order\nReceived",
                                "typenode": "vue",
                                "inputs": {},
                                "outputs": {"output_1": {"connections": [{"node": "2", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 50
                            },
                            "2": {
                                "id": 2,
                                "name": "process",
                                "data": {"name": "Contract Review"},
                                "class": "process",
                                "html": "Review Contract\nTerms & Conditions",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "1", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "3", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 150
                            },
                            "3": {
                                "id": 3,
                                "name": "process",
                                "data": {"name": "Identify Obligations"},
                                "class": "process",
                                "html": "Identify Performance\nObligations",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "2", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "4", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 250
                            },
                            "4": {
                                "id": 4,
                                "name": "process",
                                "data": {"name": "Allocate Price"},
                                "class": "process",
                                "html": "Allocate Transaction\nPrice",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "3", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "5", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 350
                            },
                            "5": {
                                "id": 5,
                                "name": "decision",
                                "data": {"name": "Obligation Satisfied?"},
                                "class": "decision",
                                "html": "Performance\nObligation\nSatisfied?",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "4", "input": "output_1"}]}},
                                "outputs": {
                                    "output_1": {"connections": [{"node": "6", "output": "input_1"}]},
                                    "output_2": {"connections": [{"node": "7", "output": "input_1"}]}
                                },
                                "pos_x": 100,
                                "pos_y": 450
                            },
                            "6": {
                                "id": 6,
                                "name": "process",
                                "data": {"name": "Recognize Revenue"},
                                "class": "process",
                                "html": "Recognize Revenue\nin GL",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "5", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "8", "output": "input_1"}]}},
                                "pos_x": 250,
                                "pos_y": 450
                            },
                            "7": {
                                "id": 7,
                                "name": "process",
                                "data": {"name": "Defer Revenue"},
                                "class": "process",
                                "html": "Record Deferred\nRevenue",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "5", "input": "output_2"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "5", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 550
                            },
                            "8": {
                                "id": 8,
                                "name": "end",
                                "data": {"name": "Revenue Posted"},
                                "class": "end",
                                "html": "Revenue\nRecognized",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "6", "input": "output_1"}]}},
                                "outputs": {},
                                "pos_x": 250,
                                "pos_y": 550
                            }
                        }
                    }
                }
            }
        })

    elif audit_type == 'itgc':
        # User Access Review Process - links to ITGC-R001 (Unauthorized access)
        flowcharts.append({
            'name': f'user-access-review-{audit_id}',
            'risk_id': 'ITGC-R001',
            'data': {
                "drawflow": {
                    "Home": {
                        "data": {
                            "1": {
                                "id": 1,
                                "name": "start",
                                "data": {"name": "Quarterly Review Triggered"},
                                "class": "start",
                                "html": "Quarterly Review\nTriggered",
                                "typenode": "vue",
                                "inputs": {},
                                "outputs": {"output_1": {"connections": [{"node": "2", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 50
                            },
                            "2": {
                                "id": 2,
                                "name": "process",
                                "data": {"name": "Extract User List"},
                                "class": "process",
                                "html": "Extract User Access\nfrom Active Directory",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "1", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "3", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 150
                            },
                            "3": {
                                "id": 3,
                                "name": "process",
                                "data": {"name": "Distribute to Managers"},
                                "class": "process",
                                "html": "Distribute List to\nDepartment Managers",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "2", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "4", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 250
                            },
                            "4": {
                                "id": 4,
                                "name": "process",
                                "data": {"name": "Manager Review"},
                                "class": "process",
                                "html": "Manager Reviews\n& Certifies Access",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "3", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "5", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 350
                            },
                            "5": {
                                "id": 5,
                                "name": "decision",
                                "data": {"name": "Access Appropriate?"},
                                "class": "decision",
                                "html": "Is All Access\nAppropriate?",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "4", "input": "output_1"}]}},
                                "outputs": {
                                    "output_1": {"connections": [{"node": "7", "output": "input_1"}]},
                                    "output_2": {"connections": [{"node": "6", "output": "input_1"}]}
                                },
                                "pos_x": 100,
                                "pos_y": 450
                            },
                            "6": {
                                "id": 6,
                                "name": "process",
                                "data": {"name": "Remove Access"},
                                "class": "process",
                                "html": "IT Removes\nInappropriate Access",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "5", "input": "output_2"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "7", "output": "input_1"}]}},
                                "pos_x": 280,
                                "pos_y": 450
                            },
                            "7": {
                                "id": 7,
                                "name": "process",
                                "data": {"name": "Document Results"},
                                "class": "process",
                                "html": "Document Review\nResults",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "5", "input": "output_1"}, {"node": "6", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "8", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 550
                            },
                            "8": {
                                "id": 8,
                                "name": "end",
                                "data": {"name": "Review Complete"},
                                "class": "end",
                                "html": "Quarterly Review\nComplete",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "7", "input": "output_1"}]}},
                                "outputs": {},
                                "pos_x": 100,
                                "pos_y": 650
                            }
                        }
                    }
                }
            }
        })

        # Change Management Process - links to ITGC-R002 (Unapproved changes)
        flowcharts.append({
            'name': f'change-management-{audit_id}',
            'risk_id': 'ITGC-R002',
            'data': {
                "drawflow": {
                    "Home": {
                        "data": {
                            "1": {
                                "id": 1,
                                "name": "start",
                                "data": {"name": "Change Request Submitted"},
                                "class": "start",
                                "html": "Change Request\nSubmitted",
                                "typenode": "vue",
                                "inputs": {},
                                "outputs": {"output_1": {"connections": [{"node": "2", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 50
                            },
                            "2": {
                                "id": 2,
                                "name": "process",
                                "data": {"name": "Initial Review"},
                                "class": "process",
                                "html": "Technical Review\n& Impact Assessment",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "1", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "3", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 150
                            },
                            "3": {
                                "id": 3,
                                "name": "process",
                                "data": {"name": "CAB Review"},
                                "class": "process",
                                "html": "Change Advisory\nBoard Review",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "2", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "4", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 250
                            },
                            "4": {
                                "id": 4,
                                "name": "decision",
                                "data": {"name": "Approved?"},
                                "class": "decision",
                                "html": "CAB\nApproved?",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "3", "input": "output_1"}]}},
                                "outputs": {
                                    "output_1": {"connections": [{"node": "5", "output": "input_1"}]},
                                    "output_2": {"connections": [{"node": "9", "output": "input_1"}]}
                                },
                                "pos_x": 100,
                                "pos_y": 350
                            },
                            "5": {
                                "id": 5,
                                "name": "process",
                                "data": {"name": "Development"},
                                "class": "process",
                                "html": "Develop Change\nin Dev Environment",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "4", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "6", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 450
                            },
                            "6": {
                                "id": 6,
                                "name": "process",
                                "data": {"name": "Testing"},
                                "class": "process",
                                "html": "Test in UAT\nEnvironment",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "5", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "7", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 550
                            },
                            "7": {
                                "id": 7,
                                "name": "process",
                                "data": {"name": "Deployment"},
                                "class": "process",
                                "html": "Deploy to Production\n(Segregated)",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "6", "input": "output_1"}]}},
                                "outputs": {"output_1": {"connections": [{"node": "8", "output": "input_1"}]}},
                                "pos_x": 100,
                                "pos_y": 650
                            },
                            "8": {
                                "id": 8,
                                "name": "end",
                                "data": {"name": "Change Deployed"},
                                "class": "end",
                                "html": "Change\nComplete",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "7", "input": "output_1"}]}},
                                "outputs": {},
                                "pos_x": 100,
                                "pos_y": 750
                            },
                            "9": {
                                "id": 9,
                                "name": "end",
                                "data": {"name": "Rejected"},
                                "class": "end",
                                "html": "Change\nRejected",
                                "typenode": "vue",
                                "inputs": {"input_1": {"connections": [{"node": "4", "input": "output_2"}]}},
                                "outputs": {},
                                "pos_x": 280,
                                "pos_y": 350
                            }
                        }
                    }
                }
            }
        })

    elif audit_type == 'revenue':
        # Order-to-Cash Process - links to REV-R001 (Revenue before performance obligations)
        flowcharts.append({
            'name': f'order-to-cash-{audit_id}',
            'risk_id': 'REV-R001',
            'data': {
                "drawflow": {
                    "Home": {
                        "data": {
                            "1": {"id": 1, "name": "start", "data": {"name": "Customer Order"}, "class": "start", "html": "Customer Order\nReceived", "typenode": "vue", "inputs": {}, "outputs": {"output_1": {"connections": [{"node": "2", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 50},
                            "2": {"id": 2, "name": "process", "data": {"name": "Credit Check"}, "class": "process", "html": "Credit Check\n& Approval", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "1", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "3", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 150},
                            "3": {"id": 3, "name": "process", "data": {"name": "Order Entry"}, "class": "process", "html": "Enter Order\nin System", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "2", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "4", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 250},
                            "4": {"id": 4, "name": "process", "data": {"name": "Fulfillment"}, "class": "process", "html": "Ship Product/\nDeliver Service", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "3", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "5", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 350},
                            "5": {"id": 5, "name": "process", "data": {"name": "Invoice"}, "class": "process", "html": "Generate\nInvoice", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "4", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "6", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 450},
                            "6": {"id": 6, "name": "process", "data": {"name": "Revenue Recognition"}, "class": "process", "html": "Recognize\nRevenue", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "5", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "7", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 550},
                            "7": {"id": 7, "name": "process", "data": {"name": "Collection"}, "class": "process", "html": "Collect\nPayment", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "6", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "8", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 650},
                            "8": {"id": 8, "name": "end", "data": {"name": "Cash Applied"}, "class": "end", "html": "Cash Applied\nto AR", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "7", "input": "output_1"}]}}, "outputs": {}, "pos_x": 100, "pos_y": 750}
                        }
                    }
                }
            }
        })

        # Credit Memo Process - links to REV-R004 (Credit/adjustment controls)
        flowcharts.append({
            'name': f'credit-memo-process-{audit_id}',
            'risk_id': 'REV-R004',
            'data': {
                "drawflow": {
                    "Home": {
                        "data": {
                            "1": {"id": 1, "name": "start", "data": {"name": "Credit Request"}, "class": "start", "html": "Customer Credit\nRequest", "typenode": "vue", "inputs": {}, "outputs": {"output_1": {"connections": [{"node": "2", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 50},
                            "2": {"id": 2, "name": "process", "data": {"name": "Log Request"}, "class": "process", "html": "Log in CRM\nSystem", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "1", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "3", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 150},
                            "3": {"id": 3, "name": "process", "data": {"name": "Review"}, "class": "process", "html": "AR Team\nReviews", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "2", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "4", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 250},
                            "4": {"id": 4, "name": "decision", "data": {"name": "Amount Check"}, "class": "decision", "html": "Amount\n> $5,000?", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "3", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "5", "output": "input_1"}]}, "output_2": {"connections": [{"node": "6", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 350},
                            "5": {"id": 5, "name": "process", "data": {"name": "Manager Approval"}, "class": "process", "html": "Manager\nApproval", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "4", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "6", "output": "input_1"}]}}, "pos_x": 280, "pos_y": 350},
                            "6": {"id": 6, "name": "process", "data": {"name": "Post Credit"}, "class": "process", "html": "Post Credit\nMemo", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "4", "input": "output_2"}, {"node": "5", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "7", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 450},
                            "7": {"id": 7, "name": "end", "data": {"name": "Complete"}, "class": "end", "html": "Credit\nApplied", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "6", "input": "output_1"}]}}, "outputs": {}, "pos_x": 100, "pos_y": 550}
                        }
                    }
                }
            }
        })

    elif audit_type == 'vendor':
        # Vendor Onboarding Process - links to VND-R001 (Critical vendor identification)
        flowcharts.append({
            'name': f'vendor-onboarding-{audit_id}',
            'risk_id': 'VND-R001',
            'data': {
                "drawflow": {
                    "Home": {
                        "data": {
                            "1": {"id": 1, "name": "start", "data": {"name": "Vendor Request"}, "class": "start", "html": "New Vendor\nRequest", "typenode": "vue", "inputs": {}, "outputs": {"output_1": {"connections": [{"node": "2", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 50},
                            "2": {"id": 2, "name": "process", "data": {"name": "Risk Assessment"}, "class": "process", "html": "Complete Risk\nAssessment", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "1", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "3", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 150},
                            "3": {"id": 3, "name": "process", "data": {"name": "Assign Tier"}, "class": "process", "html": "Assign Risk\nTier", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "2", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "4", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 250},
                            "4": {"id": 4, "name": "decision", "data": {"name": "Data Handler?"}, "class": "decision", "html": "Handles\nSensitive Data?", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "3", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "5", "output": "input_1"}]}, "output_2": {"connections": [{"node": "6", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 350},
                            "5": {"id": 5, "name": "process", "data": {"name": "Security Review"}, "class": "process", "html": "Security Team\nReview", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "4", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "6", "output": "input_1"}]}}, "pos_x": 280, "pos_y": 350},
                            "6": {"id": 6, "name": "process", "data": {"name": "Contract"}, "class": "process", "html": "Execute MSA\n& DPA", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "4", "input": "output_2"}, {"node": "5", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "7", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 450},
                            "7": {"id": 7, "name": "process", "data": {"name": "Setup"}, "class": "process", "html": "Setup in\nProcurement", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "6", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "8", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 550},
                            "8": {"id": 8, "name": "end", "data": {"name": "Active"}, "class": "end", "html": "Vendor\nActive", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "7", "input": "output_1"}]}}, "outputs": {}, "pos_x": 100, "pos_y": 650}
                        }
                    }
                }
            }
        })

        # Vendor Performance Review - links to VND-R002 (SLA monitoring)
        flowcharts.append({
            'name': f'vendor-performance-review-{audit_id}',
            'risk_id': 'VND-R002',
            'data': {
                "drawflow": {
                    "Home": {
                        "data": {
                            "1": {"id": 1, "name": "start", "data": {"name": "Quarter End"}, "class": "start", "html": "Quarter End\nTrigger", "typenode": "vue", "inputs": {}, "outputs": {"output_1": {"connections": [{"node": "2", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 50},
                            "2": {"id": 2, "name": "process", "data": {"name": "Gather SLAs"}, "class": "process", "html": "Gather SLA\nMetrics", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "1", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "3", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 150},
                            "3": {"id": 3, "name": "process", "data": {"name": "Prepare Scorecard"}, "class": "process", "html": "Prepare\nScorecard", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "2", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "4", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 250},
                            "4": {"id": 4, "name": "process", "data": {"name": "QBR Meeting"}, "class": "process", "html": "Conduct QBR\nMeeting", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "3", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "5", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 350},
                            "5": {"id": 5, "name": "decision", "data": {"name": "Issues?"}, "class": "decision", "html": "Performance\nIssues?", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "4", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "6", "output": "input_1"}]}, "output_2": {"connections": [{"node": "7", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 450},
                            "6": {"id": 6, "name": "process", "data": {"name": "Remediation"}, "class": "process", "html": "Create\nRemediation Plan", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "5", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "7", "output": "input_1"}]}}, "pos_x": 280, "pos_y": 450},
                            "7": {"id": 7, "name": "end", "data": {"name": "Document"}, "class": "end", "html": "Document\nResults", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "5", "input": "output_2"}, {"node": "6", "input": "output_1"}]}}, "outputs": {}, "pos_x": 100, "pos_y": 550}
                        }
                    }
                }
            }
        })

    elif audit_type == 'cyber':
        # Incident Response Process - links to CYB-R001 (Incident response)
        flowcharts.append({
            'name': f'incident-response-{audit_id}',
            'risk_id': 'CYB-R001',
            'data': {
                "drawflow": {
                    "Home": {
                        "data": {
                            "1": {"id": 1, "name": "start", "data": {"name": "Alert Triggered"}, "class": "start", "html": "SIEM Alert\nTriggered", "typenode": "vue", "inputs": {}, "outputs": {"output_1": {"connections": [{"node": "2", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 50},
                            "2": {"id": 2, "name": "process", "data": {"name": "SOC Triage"}, "class": "process", "html": "SOC Analyst\nTriage", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "1", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "3", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 150},
                            "3": {"id": 3, "name": "decision", "data": {"name": "Valid Threat?"}, "class": "decision", "html": "Confirmed\nThreat?", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "2", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "4", "output": "input_1"}]}, "output_2": {"connections": [{"node": "8", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 250},
                            "4": {"id": 4, "name": "process", "data": {"name": "Containment"}, "class": "process", "html": "Contain\nThreat", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "3", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "5", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 350},
                            "5": {"id": 5, "name": "process", "data": {"name": "Investigation"}, "class": "process", "html": "Investigate\nRoot Cause", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "4", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "6", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 450},
                            "6": {"id": 6, "name": "process", "data": {"name": "Eradication"}, "class": "process", "html": "Eradicate\n& Recover", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "5", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "7", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 550},
                            "7": {"id": 7, "name": "process", "data": {"name": "Lessons Learned"}, "class": "process", "html": "Document\nLessons Learned", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "6", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "9", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 650},
                            "8": {"id": 8, "name": "process", "data": {"name": "Close FP"}, "class": "process", "html": "Close as\nFalse Positive", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "3", "input": "output_2"}]}}, "outputs": {"output_1": {"connections": [{"node": "9", "output": "input_1"}]}}, "pos_x": 280, "pos_y": 250},
                            "9": {"id": 9, "name": "end", "data": {"name": "Closed"}, "class": "end", "html": "Incident\nClosed", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "7", "input": "output_1"}, {"node": "8", "input": "output_1"}]}}, "outputs": {}, "pos_x": 100, "pos_y": 750}
                        }
                    }
                }
            }
        })

        # Vulnerability Management Process - links to CYB-R002 (Vulnerability management)
        flowcharts.append({
            'name': f'vulnerability-management-{audit_id}',
            'risk_id': 'CYB-R002',
            'data': {
                "drawflow": {
                    "Home": {
                        "data": {
                            "1": {"id": 1, "name": "start", "data": {"name": "Scan Complete"}, "class": "start", "html": "Vulnerability\nScan Complete", "typenode": "vue", "inputs": {}, "outputs": {"output_1": {"connections": [{"node": "2", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 50},
                            "2": {"id": 2, "name": "process", "data": {"name": "Analyze Results"}, "class": "process", "html": "Analyze\nFindings", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "1", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "3", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 150},
                            "3": {"id": 3, "name": "process", "data": {"name": "Prioritize"}, "class": "process", "html": "Prioritize by\nCVSS Score", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "2", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "4", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 250},
                            "4": {"id": 4, "name": "process", "data": {"name": "Create Tickets"}, "class": "process", "html": "Create\nRemediation Tickets", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "3", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "5", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 350},
                            "5": {"id": 5, "name": "process", "data": {"name": "Remediate"}, "class": "process", "html": "Apply Patches/\nMitigations", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "4", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "6", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 450},
                            "6": {"id": 6, "name": "process", "data": {"name": "Verify"}, "class": "process", "html": "Verify\nRemediation", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "5", "input": "output_1"}]}}, "outputs": {"output_1": {"connections": [{"node": "7", "output": "input_1"}]}}, "pos_x": 100, "pos_y": 550},
                            "7": {"id": 7, "name": "end", "data": {"name": "Closed"}, "class": "end", "html": "Vulnerability\nClosed", "typenode": "vue", "inputs": {"input_1": {"connections": [{"node": "6", "input": "output_1"}]}}, "outputs": {}, "pos_x": 100, "pos_y": 650}
                        }
                    }
                }
            }
        })

    # Save flowcharts to database
    for fc in flowcharts:
        db.save_flowchart(fc['name'], fc['data'], risk_id=fc.get('risk_id'), audit_id=audit_id)

    return len(flowcharts)


def assign_admin_to_audits(db, audit_ids):
    """Assign the default admin user to all audits."""
    # Get admin user (should be ID 1)
    admin = db.get_user_by_email('admin@localhost')
    if not admin:
        print("  Warning: Admin user not found, skipping membership assignment")
        return

    # Get auditor role (ID 2)
    auditor_role = db.get_role_by_name('auditor')
    if not auditor_role:
        print("  Warning: Auditor role not found")
        return

    for audit_id in audit_ids:
        # Check if membership exists
        existing = db.get_audit_membership(admin['id'], audit_id)
        if not existing:
            db.add_audit_membership(audit_id, admin['id'], auditor_role['id'])
            print(f"  Assigned admin to audit {audit_id}")


def clear_existing_data(db):
    """Clear all existing audit data to start fresh."""
    conn = db._get_conn()
    # Clear RACM data
    conn.execute("DELETE FROM tasks")
    conn.execute("DELETE FROM issues")
    conn.execute("DELETE FROM risks")
    conn.execute("DELETE FROM flowcharts")
    conn.execute("DELETE FROM test_documents")
    conn.execute("DELETE FROM risk_attachments")
    conn.execute("DELETE FROM issue_attachments")
    # Clear audit memberships and audits
    conn.execute("DELETE FROM audit_memberships")
    conn.execute("DELETE FROM audits")
    conn.commit()
    conn.close()
    print("  Cleared all existing audit data")


def main():
    print("SmartPapers Seed Data Script")
    print("=" * 40)

    db = get_db()

    # Clear existing data
    print("\n1. Clearing existing data...")
    clear_existing_data(db)

    # Create audits
    print("\n2. Creating audits...")
    audit_ids = seed_audits(db)

    flowchart_count = 0
    if len(audit_ids) >= 5:
        # Seed data for each audit
        print("\n3. Seeding SOX Compliance audit...")
        seed_sox_audit(db, audit_ids[0])

        print("\n4. Seeding IT General Controls audit...")
        seed_itgc_audit(db, audit_ids[1])

        print("\n5. Seeding Revenue Cycle audit...")
        seed_revenue_audit(db, audit_ids[2])

        print("\n6. Seeding Vendor Management audit...")
        seed_vendor_audit(db, audit_ids[3])

        print("\n7. Seeding Cybersecurity audit...")
        seed_cyber_audit(db, audit_ids[4])

        # Seed flowcharts for ALL audits
        print("\n8. Creating process flowcharts...")
        flowchart_count += seed_flowcharts(db, audit_ids[0], 'sox')
        print(f"  Added 2 flowcharts for SOX audit (Financial Close, Revenue Recognition)")
        flowchart_count += seed_flowcharts(db, audit_ids[1], 'itgc')
        print(f"  Added 2 flowcharts for ITGC audit (User Access Review, Change Management)")
        flowchart_count += seed_flowcharts(db, audit_ids[2], 'revenue')
        print(f"  Added 2 flowcharts for Revenue audit (Order-to-Cash, Credit Memo)")
        flowchart_count += seed_flowcharts(db, audit_ids[3], 'vendor')
        print(f"  Added 2 flowcharts for Vendor audit (Onboarding, Performance Review)")
        flowchart_count += seed_flowcharts(db, audit_ids[4], 'cyber')
        print(f"  Added 2 flowcharts for Cybersecurity audit (Incident Response, Vulnerability Management)")

        # Assign admin to all audits
        print("\n9. Assigning admin user to audits...")
        assign_admin_to_audits(db, audit_ids)

    print("\n" + "=" * 40)
    print("Seed data complete!")
    print(f"Created {len(audit_ids)} audits with RACM data and {flowchart_count} flowcharts")
    print("\nYou can now log in and select an audit to view its workpapers.")


if __name__ == '__main__':
    main()
