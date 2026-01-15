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
            'description': 'Annual SOX 404 compliance audit covering key financial controls',
            'audit_type': 'Compliance',
            'status': 'In Progress',
            'risk_rating': 'High',
            'start_date': '2026-01-15',
            'end_date': '2026-03-31',
            'lead_auditor': 'Sarah Chen',
            'department': 'Finance'
        },
        {
            'title': 'IT General Controls',
            'description': 'Review of IT general controls including access management, change management, and operations',
            'audit_type': 'IT Audit',
            'status': 'Planning',
            'risk_rating': 'Medium',
            'start_date': '2026-02-01',
            'end_date': '2026-04-15',
            'lead_auditor': 'Michael Torres',
            'department': 'Information Technology'
        },
        {
            'title': 'Revenue Cycle Audit',
            'description': 'End-to-end review of revenue recognition, billing, and collections processes',
            'audit_type': 'Operational',
            'status': 'Planning',
            'risk_rating': 'High',
            'start_date': '2026-03-01',
            'end_date': '2026-05-15',
            'lead_auditor': 'Jennifer Adams',
            'department': 'Sales & Finance'
        },
        {
            'title': 'Vendor Management Review',
            'description': 'Assessment of third-party vendor oversight and contract compliance',
            'audit_type': 'Compliance',
            'status': 'Not Started',
            'risk_rating': 'Medium',
            'start_date': '2026-04-01',
            'end_date': '2026-05-31',
            'lead_auditor': 'David Park',
            'department': 'Procurement'
        },
        {
            'title': 'Cybersecurity Assessment',
            'description': 'Comprehensive review of cybersecurity controls and incident response capabilities',
            'audit_type': 'IT Audit',
            'status': 'Not Started',
            'risk_rating': 'Critical',
            'start_date': '2026-05-01',
            'end_date': '2026-07-31',
            'lead_auditor': 'Michael Torres',
            'department': 'Information Security'
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
            audit_type=audit['audit_type'],
            status=audit['status'],
            risk_rating=audit['risk_rating'],
            start_date=audit['start_date'],
            end_date=audit['end_date'],
            lead_auditor=audit['lead_auditor'],
            department=audit['department']
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
            'status': 'Complete'
        },
        {
            'risk_id': 'SOX-R002',
            'risk': 'Unauthorized journal entries could be posted without proper approval',
            'control_id': 'All journal entries over $10,000 require dual approval in the ERP system',
            'control_owner': 'Controller',
            'status': 'In Progress'
        },
        {
            'risk_id': 'SOX-R003',
            'risk': 'Revenue may be recognized in incorrect periods',
            'control_id': 'Revenue recognition review performed monthly with cutoff testing',
            'control_owner': 'Revenue Accounting Manager',
            'status': 'Not Started'
        },
        {
            'risk_id': 'SOX-R004',
            'risk': 'Account reconciliations may not identify errors timely',
            'control_id': 'Monthly reconciliation of all balance sheet accounts with supervisory review',
            'control_owner': 'Accounting Manager',
            'status': 'Complete'
        },
        {
            'risk_id': 'SOX-R005',
            'risk': 'Segregation of duties violations in financial systems',
            'control_id': 'Quarterly access review of financial system roles and permissions',
            'control_owner': 'IT Security Manager',
            'status': 'In Progress'
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
        # Update audit_id
        conn = db._get_conn()
        conn.execute("UPDATE risks SET audit_id = ? WHERE id = ?", (audit_id, row_id))
        conn.commit()
        conn.close()
        risk_ids.append(row_id)

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

    print(f"  Added {len(risks)} risks, {len(issues)} issues, {len(tasks)} tasks to SOX audit")


def seed_itgc_audit(db, audit_id):
    """Seed RACM and issues for IT General Controls audit."""
    risks = [
        {
            'risk_id': 'ITGC-R001',
            'risk': 'Unauthorized access to production systems due to weak access controls',
            'control_id': 'Quarterly access review with manager certification of user access rights',
            'control_owner': 'IT Security Manager',
            'status': 'In Progress'
        },
        {
            'risk_id': 'ITGC-R002',
            'risk': 'Unapproved changes to production code could introduce errors or vulnerabilities',
            'control_id': 'Change management process with CAB approval and segregated deployment',
            'control_owner': 'IT Operations Manager',
            'status': 'Not Started'
        },
        {
            'risk_id': 'ITGC-R003',
            'risk': 'System outages due to inadequate backup and recovery procedures',
            'control_id': 'Daily backups with monthly restoration testing and documented recovery plans',
            'control_owner': 'Infrastructure Manager',
            'status': 'Not Started'
        },
        {
            'risk_id': 'ITGC-R004',
            'risk': 'Privileged access abuse by system administrators',
            'control_id': 'Privileged access management (PAM) solution with session recording',
            'control_owner': 'IT Security Manager',
            'status': 'Planning'
        },
        {
            'risk_id': 'ITGC-R005',
            'risk': 'Data loss from terminated employee accounts not disabled timely',
            'control_id': 'HR-IT integration for automated account disablement within 24 hours',
            'control_owner': 'HR Systems Manager',
            'status': 'Not Started'
        },
        {
            'risk_id': 'ITGC-R006',
            'risk': 'Batch job failures may go undetected',
            'control_id': 'Automated monitoring of critical batch jobs with alerting to operations team',
            'control_owner': 'IT Operations Manager',
            'status': 'Not Started'
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
        conn.execute("UPDATE risks SET audit_id = ? WHERE id = ?", (audit_id, row_id))
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

    # Create tasks
    tasks = [
        {'title': 'Pull user access listing', 'description': 'Extract from Active Directory and key applications', 'column_id': 'planning', 'priority': 'high'},
        {'title': 'Review change tickets', 'description': 'Sample 30 changes from Q4', 'column_id': 'planning', 'priority': 'medium'},
        {'title': 'Test backup restoration', 'description': 'Observe monthly backup test', 'column_id': 'planning', 'priority': 'medium'},
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

    print(f"  Added {len(risks)} risks, {len(issues)} issues, {len(tasks)} tasks to ITGC audit")


def seed_revenue_audit(db, audit_id):
    """Seed RACM and issues for Revenue Cycle audit."""
    risks = [
        {
            'risk_id': 'REV-R001',
            'risk': 'Revenue recognized before performance obligations are satisfied',
            'control_id': 'Contract review checklist ensuring delivery/acceptance before revenue posting',
            'control_owner': 'Revenue Recognition Manager',
            'status': 'Not Started'
        },
        {
            'risk_id': 'REV-R002',
            'risk': 'Customer credits and returns not recorded timely',
            'control_id': 'Daily review of credit memo requests with 48-hour processing SLA',
            'control_owner': 'AR Manager',
            'status': 'Not Started'
        },
        {
            'risk_id': 'REV-R003',
            'risk': 'Unbilled revenue not identified and recorded',
            'control_id': 'Weekly unbilled revenue report review with follow-up on aged items',
            'control_owner': 'Billing Manager',
            'status': 'Not Started'
        },
        {
            'risk_id': 'REV-R004',
            'risk': 'Sales commissions calculated incorrectly',
            'control_id': 'Monthly commission calculation review with sales operations sign-off',
            'control_owner': 'Sales Operations Director',
            'status': 'Not Started'
        },
        {
            'risk_id': 'REV-R005',
            'risk': 'Customer pricing errors in billing system',
            'control_id': 'Price change approval workflow with system update verification',
            'control_owner': 'Pricing Manager',
            'status': 'Not Started'
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
        conn.execute("UPDATE risks SET audit_id = ? WHERE id = ?", (audit_id, row_id))
        conn.commit()
        conn.close()

    # Create tasks
    tasks = [
        {'title': 'Map revenue process', 'description': 'Document order-to-cash workflow', 'column_id': 'planning', 'priority': 'high'},
        {'title': 'Identify key contracts', 'description': 'Select sample of material contracts for review', 'column_id': 'planning', 'priority': 'high'},
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

    print(f"  Added {len(risks)} risks, 0 issues, {len(tasks)} tasks to Revenue audit")


def seed_vendor_audit(db, audit_id):
    """Seed RACM for Vendor Management audit."""
    risks = [
        {
            'risk_id': 'VND-R001',
            'risk': 'Critical vendors not identified and monitored appropriately',
            'control_id': 'Annual vendor risk assessment with tiering based on criticality',
            'control_owner': 'Vendor Management Director',
            'status': 'Not Started'
        },
        {
            'risk_id': 'VND-R002',
            'risk': 'Vendor contracts may not include required security and compliance terms',
            'control_id': 'Contract template with mandatory security addendum for data-handling vendors',
            'control_owner': 'Legal Counsel',
            'status': 'Not Started'
        },
        {
            'risk_id': 'VND-R003',
            'risk': 'Vendor performance issues not identified timely',
            'control_id': 'Quarterly business review with SLA tracking for critical vendors',
            'control_owner': 'Vendor Management Director',
            'status': 'Not Started'
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
        conn.execute("UPDATE risks SET audit_id = ? WHERE id = ?", (audit_id, row_id))
        conn.commit()
        conn.close()

    print(f"  Added {len(risks)} risks, 0 issues, 0 tasks to Vendor audit")


def seed_cyber_audit(db, audit_id):
    """Seed RACM for Cybersecurity audit."""
    risks = [
        {
            'risk_id': 'CYB-R001',
            'risk': 'Phishing attacks may compromise user credentials',
            'control_id': 'Mandatory security awareness training with quarterly phishing simulations',
            'control_owner': 'CISO',
            'status': 'Not Started'
        },
        {
            'risk_id': 'CYB-R002',
            'risk': 'Unpatched vulnerabilities in internet-facing systems',
            'control_id': 'Monthly vulnerability scanning with 30-day critical patch SLA',
            'control_owner': 'Security Operations Manager',
            'status': 'Not Started'
        },
        {
            'risk_id': 'CYB-R003',
            'risk': 'Security incidents not detected or responded to timely',
            'control_id': 'SIEM monitoring with 24/7 SOC coverage and incident response playbooks',
            'control_owner': 'Security Operations Manager',
            'status': 'Not Started'
        },
        {
            'risk_id': 'CYB-R004',
            'risk': 'Sensitive data exposed through misconfigured cloud resources',
            'control_id': 'Cloud security posture management (CSPM) with automated remediation',
            'control_owner': 'Cloud Security Architect',
            'status': 'Not Started'
        },
        {
            'risk_id': 'CYB-R005',
            'risk': 'Ransomware attack could disrupt business operations',
            'control_id': 'Endpoint detection and response (EDR) with network segmentation',
            'control_owner': 'CISO',
            'status': 'Not Started'
        },
        {
            'risk_id': 'CYB-R006',
            'risk': 'Third-party integrations may introduce security vulnerabilities',
            'control_id': 'API security gateway with authentication and rate limiting',
            'control_owner': 'Application Security Manager',
            'status': 'Not Started'
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
        conn.execute("UPDATE risks SET audit_id = ? WHERE id = ?", (audit_id, row_id))
        conn.commit()
        conn.close()

    print(f"  Added {len(risks)} risks, 0 issues, 0 tasks to Cybersecurity audit")


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
    """Clear existing RACM data (but keep audits and users)."""
    conn = db._get_conn()
    conn.execute("DELETE FROM tasks")
    conn.execute("DELETE FROM issues")
    conn.execute("DELETE FROM risks")
    conn.execute("DELETE FROM flowcharts")
    conn.execute("DELETE FROM test_documents")
    conn.commit()
    conn.close()
    print("  Cleared existing RACM data")


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

        # Assign admin to all audits
        print("\n8. Assigning admin user to audits...")
        assign_admin_to_audits(db, audit_ids)

    print("\n" + "=" * 40)
    print("Seed data complete!")
    print(f"Created {len(audit_ids)} audits with RACM data")
    print("\nYou can now log in and select an audit to view its workpapers.")


if __name__ == '__main__':
    main()
