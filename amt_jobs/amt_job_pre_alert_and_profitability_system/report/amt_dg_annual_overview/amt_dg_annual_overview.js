frappe.query_reports['AMT DG Annual Overview'] = {
    filters: [
        {
            fieldname: 'year',
            label: 'Year',
            fieldtype: 'Select',
            options: '\n2026\n2025\n2024\n2023\n2022\n2021\n2020\n2019',
        },
        {
            fieldname: 'department',
            label: 'Department',
            fieldtype: 'Select',
            options: '\nTransit\nShipping\nLogistics\nPSS\nLIMA Oil Base',
        },
    ]
};
