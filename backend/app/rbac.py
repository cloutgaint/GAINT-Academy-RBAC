ROLE_MENUS = {
    "Institution Admin": [
        "Dashboard", "Students", "Staff", "Admissions", "Academics", "Timetable",
        "Attendance", "Exams & Results", "Communication", "Learning / LMS",
        "Events", "Grievance", "Fees & Payments", "Transport", "Library",
        "Hostel", "Inventory & Assets", "Visitors", "Health", "Reports",
        "Users & Roles", "Audit",
    ],
    "Teacher": [
        "Dashboard", "My Classes", "My Students", "Timetable", "Attendance",
        "Homework", "Assignments", "Exams", "Results", "Teacher Notes",
        "Communication", "Events", "Library", "Leave",
    ],
    "Student": [
        "Dashboard", "My Profile", "Timetable", "Attendance", "Courses",
        "Homework", "Assignments", "Exams", "Results", "Fees", "Transport",
        "Library", "Events", "Grievance", "Leave Request", "My Safety",
    ],
    "Parent / Guardian": [
        "Dashboard", "My Children", "Attendance", "Homework", "Results", "Fees",
        "Transport", "Live Location", "Messages", "Events", "Grievance",
        "Leave Request",
    ],
    "Accounts": [
        "Dashboard", "Fees", "Payments", "Receipts", "Concessions", "Refunds",
        "Reconciliation", "Finance Reports",
    ],
    "HR": [
        "Dashboard", "Staff", "Attendance", "Leave", "Documents", "Recruitment",
        "Performance", "HR Reports",
    ],
    "Campus Admin": [
        "Dashboard", "Students", "Staff", "Campus Attendance", "Transport",
        "Live Safety Map", "Visitors", "Inventory", "Assets", "Events",
        "Grievance", "Reports",
    ],
    "Auditor": [
        "Dashboard", "Audit Trail", "Compliance", "Exception Reports",
        "Evidence", "Export Reports",
    ],
}

PAGE_POLICY = {
    "Institution Admin": {
        "Students": {"create", "update", "delete"},
        "Staff": {"create", "update", "delete"},
        "Admissions": {"create", "update", "approve"},
        "Academics": {"create", "update"},
        "Timetable": {"create", "update"},
        "Attendance": {"create", "update"},
        "Exams & Results": {"create", "update", "approve"},
        "Communication": {"create", "update", "message"},
        "Learning / LMS": {"create", "update"},
        "Events": {"create", "update"},
        "Grievance": {"update", "approve"},
        "Fees & Payments": {"create", "update", "approve", "export"},
        "Transport": {"create", "update"},
        "Library": {"create", "update"},
        "Hostel": {"create", "update"},
        "Inventory & Assets": {"create", "update", "delete"},
        "Visitors": {"create", "update"},
        "Health": {"create", "update"},
        "Reports": {"export"},
        "Users & Roles": {"create", "update", "delete", "manage_users"},
        "Audit": {"view", "export"},
    },
    "Teacher": {
        "My Classes": {"view"},
        "My Students": {"view"},
        "Timetable": {"view"},
        "Attendance": {"create", "update"},
        "Homework": {"create", "update"},
        "Assignments": {"create", "update"},
        "Exams": {"create", "update"},
        "Results": {"create", "update"},
        "Teacher Notes": {"create", "update"},
        "Communication": {"create", "message"},
        "Events": {"view"},
        "Library": {"view"},
        "Leave": {"view", "create"},
    },
    "Student": {
        "My Profile": {"view"},
        "Timetable": {"view"},
        "Attendance": {"view"},
        "Courses": {"view"},
        "Homework": {"view"},
        "Assignments": {"view"},
        "Exams": {"view"},
        "Results": {"view"},
        "Fees": {"view", "pay"},
        "Transport": {"view"},
        "Library": {"view"},
        "Events": {"view"},
        "Grievance": {"view", "create_grievance"},
        "Leave Request": {"view", "request_leave"},
        "My Safety": {"view"},
    },
    "Parent / Guardian": {
        "My Children": {"view"},
        "Attendance": {"view"},
        "Homework": {"view"},
        "Results": {"view"},
        "Fees": {"view", "pay"},
        "Transport": {"view"},
        "Live Location": {"view", "track"},
        "Messages": {"view", "message"},
        "Events": {"view"},
        "Grievance": {"view", "create_grievance"},
        "Leave Request": {"view", "request_leave"},
    },
    "Accounts": {
        "Fees": {"create", "update"},
        "Payments": {"create", "update"},
        "Receipts": {"create", "export"},
        "Concessions": {"create", "update", "approve"},
        "Refunds": {"create", "update", "approve"},
        "Reconciliation": {"create", "update"},
        "Finance Reports": {"view", "export"},
    },
    "HR": {
        "Staff": {"create", "update"},
        "Attendance": {"create", "update"},
        "Leave": {"create", "update", "approve"},
        "Documents": {"create", "update"},
        "Recruitment": {"create", "update"},
        "Performance": {"create", "update"},
        "HR Reports": {"view", "export"},
    },
    "Campus Admin": {
        "Students": {"view", "update"},
        "Staff": {"view", "update"},
        "Campus Attendance": {"create", "update"},
        "Transport": {"create", "update"},
        "Live Safety Map": {"view", "track"},
        "Visitors": {"create", "update"},
        "Inventory": {"create", "update"},
        "Assets": {"create", "update"},
        "Events": {"create", "update"},
        "Grievance": {"view", "update", "approve"},
        "Reports": {"view", "export"},
    },
    "Auditor": {
        "Audit Trail": {"view", "export"},
        "Compliance": {"view", "export"},
        "Exception Reports": {"view", "export"},
        "Evidence": {"view", "export"},
        "Export Reports": {"view", "export"},
    },
}


def get_role_menu(role: str):
    return ROLE_MENUS.get(role, ["Dashboard"])


def page_permissions(role: str, page: str):
    if role not in ROLE_MENUS:
        return set()

    if page == "Dashboard":
        return {"view"}

    if page not in ROLE_MENUS[role]:
        return set()

    return {"view"} | set(PAGE_POLICY.get(role, {}).get(page, set()))


def can(role: str, page: str, action: str):
    return action in page_permissions(role, page)


def module_access_for(role: str, page: str):
    permissions = page_permissions(role, page)
    record_mutations = {"create", "update", "delete"}

    return {
        "role": role,
        "page": page,
        "permissions": sorted(permissions),
        "read_only": not bool(permissions & record_mutations),
        "can_view": "view" in permissions,
        "can_create": "create" in permissions,
        "can_update": "update" in permissions,
        "can_delete": "delete" in permissions,
        "can_approve": "approve" in permissions,
        "can_export": "export" in permissions,
        "can_pay": "pay" in permissions,
        "can_message": "message" in permissions,
        "can_track": "track" in permissions,
        "can_create_grievance": "create_grievance" in permissions,
        "can_request_leave": "request_leave" in permissions,
        "can_manage_users": "manage_users" in permissions,
    }


DASHBOARDS = {
    "Institution Admin": {
        "type": "admin",
        "title": "Institution overview",
        "subtitle": "Monitor academics, finance, attendance and institution operations.",
        "cards": [
            {"label": "Total Students", "value": "2,450", "hint": "+4.8%"},
            {"label": "Present Today", "value": "92%", "hint": "+1.2%"},
            {"label": "Fee Collection", "value": "₹18.4L", "hint": "86%"},
            {"label": "Pending Actions", "value": "24", "hint": "8 urgent"},
        ],
        "quick_actions": ["Add student", "Create notice", "Generate report", "Manage users"],
    },
    "Teacher": {
        "type": "teacher",
        "title": "Teacher workspace",
        "subtitle": "Manage classes, attendance, assignments and student progress.",
        "cards": [
            {"label": "Classes Today", "value": "5", "hint": "Next 11:30 AM"},
            {"label": "Assigned Students", "value": "148", "hint": "5 sections"},
            {"label": "Attendance Pending", "value": "2", "hint": "Needs action"},
            {"label": "Assignments to Grade", "value": "37", "hint": "12 due today"},
        ],
        "quick_actions": ["Take attendance", "Post homework", "Grade assignments", "Message class"],
    },
    "Student": {
        "type": "student",
        "title": "My academic dashboard",
        "subtitle": "Your academics, attendance, assignments and safety information.",
        "cards": [
            {"label": "My Attendance", "value": "91%", "hint": "This term"},
            {"label": "Classes Today", "value": "6", "hint": "Next: Mathematics"},
            {"label": "Pending Assignments", "value": "3", "hint": "1 due today"},
            {"label": "Upcoming Exams", "value": "2", "hint": "Next in 5 days"},
        ],
        "quick_actions": ["Open timetable", "Submit assignment", "View results", "My safety"],
    },
    "Parent / Guardian": {
        "type": "parent",
        "title": "My child overview",
        "subtitle": "Monitor academics, attendance, fees and student safety.",
        "cards": [
            {"label": "Child Attendance", "value": "91%", "hint": "This term"},
            {"label": "Current Status", "value": "On School Bus", "hint": "Route A1"},
            {"label": "Fee Due", "value": "₹0", "hint": "No dues"},
            {"label": "Unread Messages", "value": "3", "hint": "Teacher updates"},
        ],
        "quick_actions": ["View live location", "Track school bus", "View results", "Message teacher"],
    },
    "Accounts": {
        "type": "accounts",
        "title": "Finance dashboard",
        "subtitle": "Manage fees, payments, receipts and reconciliation.",
        "cards": [
            {"label": "Today Collection", "value": "₹2.45L", "hint": "163 transactions"},
            {"label": "Month Collection", "value": "₹18.4L", "hint": "86% target"},
            {"label": "Pending Fees", "value": "₹6.2L", "hint": "Across students"},
            {"label": "Refund Requests", "value": "4", "hint": "Pending review"},
        ],
        "quick_actions": ["Receive payment", "Issue receipt", "Reconcile", "Export report"],
    },
    "HR": {
        "type": "hr",
        "title": "HR dashboard",
        "subtitle": "Manage employees, attendance, leave and recruitment.",
        "cards": [
            {"label": "Total Staff", "value": "186", "hint": "All departments"},
            {"label": "Present Staff", "value": "174", "hint": "93.5%"},
            {"label": "Leave Requests", "value": "8", "hint": "Pending approval"},
            {"label": "Open Positions", "value": "4", "hint": "Recruitment"},
        ],
        "quick_actions": ["Add staff", "Approve leave", "Review documents", "HR report"],
    },
    "Campus Admin": {
        "type": "campus_admin",
        "title": "Campus operations",
        "subtitle": "Monitor campus operations, safety and resources.",
        "cards": [
            {"label": "Campus Students", "value": "1,240", "hint": "Active"},
            {"label": "Campus Staff", "value": "92", "hint": "Active"},
            {"label": "Visitors Today", "value": "14", "hint": "2 on campus"},
            {"label": "Transport Alerts", "value": "2", "hint": "Needs attention"},
        ],
        "quick_actions": ["Open live safety map", "Visitor check-in", "Asset issue", "Campus report"],
    },
    "Auditor": {
        "type": "auditor",
        "title": "Audit & compliance",
        "subtitle": "Review audit trails, compliance evidence and exceptions.",
        "cards": [
            {"label": "Audit Events Today", "value": "86", "hint": "All domains"},
            {"label": "Exceptions", "value": "4", "hint": "Open"},
            {"label": "Compliance Items", "value": "12", "hint": "In review"},
            {"label": "Pending Reviews", "value": "6", "hint": "Assigned"},
        ],
        "quick_actions": ["Review audit trail", "Open exceptions", "Export evidence", "Compliance report"],
    },
}


def dashboard_for(role: str):
    return DASHBOARDS.get(
        role,
        {
            "type": "unknown",
            "title": "Dashboard",
            "subtitle": "",
            "cards": [],
            "quick_actions": [],
        },
    )
