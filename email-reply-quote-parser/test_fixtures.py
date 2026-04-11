"""
Email reply/quote parser test fixtures.

Each fixture is a dict with:
  - name:  descriptive test name
  - html:  the HTML body (or None if text-only)
  - text:  the plain text body (or None if HTML-only)
  - expected_reply:  content that should be extracted as the "new" reply
  - expected_quoted: content that should be identified as quoted/original
  - has_identifier_in_quote_only: True when the identifier "1234-2026"
        appears ONLY in the quoted section, not in the new reply
"""

# ---------------------------------------------------------------------------
# 1. Outlook Desktop reply  --  divRplyFwdMsg pattern
# ---------------------------------------------------------------------------
OUTLOOK_DESKTOP_REPLY = {
    "name": "outlook_desktop_reply_divRplyFwdMsg",
    "html": (
        '<html xmlns:v="urn:schemas-microsoft-com:vml"'
        ' xmlns:o="urn:schemas-microsoft-com:office:office"'
        ' xmlns:w="urn:schemas-microsoft-com:office:word"'
        ' xmlns:m="http://schemas.microsoft.com/office/2004/12/omml"'
        ' xmlns="http://www.w3.org/TR/REC-html40">\r\n'
        "<head>\r\n"
        '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">\r\n'
        '<meta name="Generator" content="Microsoft Word 15 (filtered medium)">\r\n'
        "<style><!--\r\n"
        "/* Font Definitions */\r\n"
        "@font-face\r\n"
        "\t{font-family:\"Cambria Math\";\r\n"
        "\tpanose-1:2 4 5 3 5 4 6 3 2 4;}\r\n"
        "@font-face\r\n"
        "\t{font-family:Calibri;\r\n"
        "\tpanose-1:2 15 5 2 2 2 4 3 2 4;}\r\n"
        "/* Style Definitions */\r\n"
        "p.MsoNormal, li.MsoNormal, div.MsoNormal\r\n"
        "\t{margin:0in;\r\n"
        "\tfont-size:11.0pt;\r\n"
        '\tfont-family:"Calibri",sans-serif;}\r\n'
        "span.EmailStyle17\r\n"
        "\t{mso-style-type:personal-compose;\r\n"
        '\tfont-family:"Calibri",sans-serif;\r\n'
        "\tcolor:windowtext;}\r\n"
        ".MsoChpDefault\r\n"
        "\t{mso-style-type:export-only;\r\n"
        '\tfont-family:"Calibri",sans-serif;}\r\n'
        "@page WordSection1\r\n"
        "\t{size:8.5in 11.0in;\r\n"
        "\tmargin:1.0in 1.0in 1.0in 1.0in;}\r\n"
        "div.WordSection1\r\n"
        "\t{page:WordSection1;}\r\n"
        "--></style>\r\n"
        "</head>\r\n"
        "<body lang=\"EN-US\" link=\"#0563C1\" vlink=\"#954F72\""
        ' style="word-wrap:break-word">\r\n'
        '<div class="WordSection1">\r\n'
        '<p class="MsoNormal">Thanks for the update, I agree we should proceed'
        " with the migration plan.</p>\r\n"
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        '<p class="MsoNormal">Can you share the timeline by Friday?</p>\r\n'
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        '<p class="MsoNormal">Best,</p>\r\n'
        '<p class="MsoNormal">Sarah</p>\r\n'
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        '<div id="divRplyFwdMsg" dir="ltr">\r\n'
        "<hr style=\"display:inline-block;width:98%\" tabindex=\"-1\">\r\n"
        '<div id="divRplyFwdMsg" dir="ltr">\r\n'
        '<font face="Calibri, sans-serif" style="font-size:11pt" color="#000000">'
        "<b>From:</b> John Smith &lt;john.smith@example.com&gt;<br>\r\n"
        "<b>Sent:</b> Wednesday, April 9, 2026 3:42 PM<br>\r\n"
        "<b>To:</b> Sarah Johnson &lt;sarah.johnson@example.com&gt;<br>\r\n"
        "<b>Subject:</b> RE: Database Migration Plan</font>\r\n"
        "</div>\r\n"
        "<div>&nbsp;</div>\r\n"
        "</div>\r\n"
        '<p class="MsoNormal">Hi Sarah,</p>\r\n'
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        '<p class="MsoNormal">I\'ve finished the assessment of the current'
        " database schema. Here are the key findings:</p>\r\n"
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        '<ul style="margin-top:0in" type="disc">\r\n'
        ' <li class="MsoNormal">47 tables need migration</li>\r\n'
        ' <li class="MsoNormal">12 stored procedures are deprecated</li>\r\n'
        ' <li class="MsoNormal">Estimated downtime: 4 hours</li>\r\n'
        "</ul>\r\n"
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        '<p class="MsoNormal">Let me know your thoughts.</p>\r\n'
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        '<p class="MsoNormal">Thanks,</p>\r\n'
        '<p class="MsoNormal">John</p>\r\n'
        "</div>\r\n"
        "</body>\r\n"
        "</html>"
    ),
    "text": (
        "Thanks for the update, I agree we should proceed with the migration plan.\r\n"
        "\r\n"
        "Can you share the timeline by Friday?\r\n"
        "\r\n"
        "Best,\r\n"
        "Sarah\r\n"
        "\r\n"
        "-----Original Message-----\r\n"
        "From: John Smith <john.smith@example.com>\r\n"
        "Sent: Wednesday, April 9, 2026 3:42 PM\r\n"
        "To: Sarah Johnson <sarah.johnson@example.com>\r\n"
        "Subject: RE: Database Migration Plan\r\n"
        "\r\n"
        "Hi Sarah,\r\n"
        "\r\n"
        "I've finished the assessment of the current database schema. Here are the key findings:\r\n"
        "\r\n"
        "  * 47 tables need migration\r\n"
        "  * 12 stored procedures are deprecated\r\n"
        "  * Estimated downtime: 4 hours\r\n"
        "\r\n"
        "Let me know your thoughts.\r\n"
        "\r\n"
        "Thanks,\r\n"
        "John\r\n"
    ),
    "expected_reply": (
        "Thanks for the update, I agree we should proceed with the migration plan.\n"
        "\n"
        "Can you share the timeline by Friday?\n"
        "\n"
        "Best,\n"
        "Sarah"
    ),
    "expected_quoted": (
        "Hi Sarah,\n"
        "\n"
        "I've finished the assessment of the current database schema. Here are the key findings:\n"
        "\n"
        "  * 47 tables need migration\n"
        "  * 12 stored procedures are deprecated\n"
        "  * Estimated downtime: 4 hours\n"
        "\n"
        "Let me know your thoughts.\n"
        "\n"
        "Thanks,\n"
        "John"
    ),
    "has_identifier_in_quote_only": False,
}


# ---------------------------------------------------------------------------
# 2. Outlook Web App (OWA) reply  --  different HTML structure
# ---------------------------------------------------------------------------
OUTLOOK_WEB_APP_REPLY = {
    "name": "outlook_web_app_owa_reply",
    "html": (
        "<!DOCTYPE html>\r\n"
        '<html dir="ltr" xmlns="http://www.w3.org/1999/xhtml">\r\n'
        "<head>\r\n"
        '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">\r\n'
        '<meta name="GENERATOR" content="MSHTML 11.00.10570.1001">\r\n'
        "<style>\r\n"
        "body {\r\n"
        '  font-family: "Segoe UI", "Helvetica Neue", sans-serif;\r\n'
        "  font-size: 12pt;\r\n"
        "  color: #000000;\r\n"
        "}\r\n"
        "p { margin: 0; }\r\n"
        "#divtagdefaultwrapper { font-size: 12pt; color: #000000;"
        ' font-family: Calibri, Helvetica, sans-serif; }\r\n'
        "</style>\r\n"
        "</head>\r\n"
        '<body fpstyle="1" ocsi="0">\r\n'
        '<div id="divtagdefaultwrapper"'
        ' style="font-size:12pt;color:#000000;'
        'font-family:Calibri,Helvetica,sans-serif;"'
        ' dir="ltr">\r\n'
        "<p>Looks good to me! Let's go ahead and schedule the deployment"
        " for next Tuesday.</p>\r\n"
        "<p><br></p>\r\n"
        "<p>-- Maria</p>\r\n"
        "</div>\r\n"
        '<hr style="display:inline-block;width:98%" tabindex="-1">\r\n'
        '<div id="divRplyFwdMsg" dir="ltr">'
        '<font face="Calibri, sans-serif" color="#000000"'
        ' style="font-size:11pt">'
        "<b>From:</b> DevOps Team &lt;devops@example.com&gt;<br>"
        "<b>Sent:</b> Thursday, April 10, 2026 9:15 AM<br>"
        "<b>To:</b> Maria Garcia &lt;maria.garcia@example.com&gt;<br>"
        "<b>Cc:</b> Tech Lead &lt;tech.lead@example.com&gt;<br>"
        "<b>Subject:</b> Deployment Approval Request - v2.4.1"
        "</font>"
        "</div>\r\n"
        '<div style="padding-top:5px">\r\n'
        "<p>Hi Maria,</p>\r\n"
        "<p><br></p>\r\n"
        "<p>We've completed all pre-deployment checks for v2.4.1. "
        "Summary:</p>\r\n"
        "<p><br></p>\r\n"
        "<p>- All 342 unit tests passing</p>\r\n"
        "<p>- Integration tests: 98.7% pass rate</p>\r\n"
        "<p>- Performance regression: none detected</p>\r\n"
        "<p><br></p>\r\n"
        "<p>Please approve at your earliest convenience.</p>\r\n"
        "<p><br></p>\r\n"
        "<p>Thanks,<br>DevOps Team</p>\r\n"
        "</div>\r\n"
        "</body>\r\n"
        "</html>"
    ),
    "text": (
        "Looks good to me! Let's go ahead and schedule the deployment"
        " for next Tuesday.\r\n"
        "\r\n"
        "-- Maria\r\n"
        "\r\n"
        "________________________________\r\n"
        "From: DevOps Team <devops@example.com>\r\n"
        "Sent: Thursday, April 10, 2026 9:15 AM\r\n"
        "To: Maria Garcia <maria.garcia@example.com>\r\n"
        "Cc: Tech Lead <tech.lead@example.com>\r\n"
        "Subject: Deployment Approval Request - v2.4.1\r\n"
        "\r\n"
        "Hi Maria,\r\n"
        "\r\n"
        "We've completed all pre-deployment checks for v2.4.1. Summary:\r\n"
        "\r\n"
        "- All 342 unit tests passing\r\n"
        "- Integration tests: 98.7% pass rate\r\n"
        "- Performance regression: none detected\r\n"
        "\r\n"
        "Please approve at your earliest convenience.\r\n"
        "\r\n"
        "Thanks,\r\n"
        "DevOps Team\r\n"
    ),
    "expected_reply": (
        "Looks good to me! Let's go ahead and schedule the deployment"
        " for next Tuesday.\n"
        "\n"
        "-- Maria"
    ),
    "expected_quoted": (
        "Hi Maria,\n"
        "\n"
        "We've completed all pre-deployment checks for v2.4.1. Summary:\n"
        "\n"
        "- All 342 unit tests passing\n"
        "- Integration tests: 98.7% pass rate\n"
        "- Performance regression: none detected\n"
        "\n"
        "Please approve at your earliest convenience.\n"
        "\n"
        "Thanks,\n"
        "DevOps Team"
    ),
    "has_identifier_in_quote_only": False,
}


# ---------------------------------------------------------------------------
# 3. Outlook reply chain (3+ messages deep)
# ---------------------------------------------------------------------------
OUTLOOK_REPLY_CHAIN_DEEP = {
    "name": "outlook_reply_chain_three_deep",
    "html": (
        '<html xmlns:v="urn:schemas-microsoft-com:vml"'
        ' xmlns:o="urn:schemas-microsoft-com:office:office"'
        ' xmlns="http://www.w3.org/TR/REC-html40">\r\n'
        "<head>\r\n"
        '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">\r\n'
        '<meta name="Generator" content="Microsoft Word 15 (filtered medium)">\r\n'
        "<style><!--\r\n"
        "p.MsoNormal, li.MsoNormal, div.MsoNormal {\r\n"
        "  margin: 0in;\r\n"
        "  font-size: 11.0pt;\r\n"
        '  font-family: "Calibri", sans-serif;\r\n'
        "}\r\n"
        "--></style>\r\n"
        "</head>\r\n"
        '<body lang="EN-US" link="#0563C1" vlink="#954F72"'
        ' style="word-wrap:break-word">\r\n'
        '<div class="WordSection1">\r\n'
        "<!-- === NEWEST REPLY (message 3) === -->\r\n"
        '<p class="MsoNormal">Perfect, Wednesday at 2pm works for me. '
        "I'll book the conference room.</p>\r\n"
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        '<p class="MsoNormal">- Alex</p>\r\n'
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        "<!-- === QUOTED: message 2 === -->\r\n"
        '<div id="divRplyFwdMsg" dir="ltr">\r\n'
        '<hr style="display:inline-block;width:98%" tabindex="-1">\r\n'
        '<font face="Calibri, sans-serif" style="font-size:11pt"'
        ' color="#000000">'
        "<b>From:</b> Priya Patel &lt;priya.patel@example.com&gt;<br>\r\n"
        "<b>Sent:</b> Tuesday, April 7, 2026 11:30 AM<br>\r\n"
        "<b>To:</b> Alex Chen &lt;alex.chen@example.com&gt;<br>\r\n"
        "<b>Subject:</b> RE: RE: Q2 Planning Session</font>\r\n"
        "</div>\r\n"
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        '<p class="MsoNormal">Hi Alex,</p>\r\n'
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        '<p class="MsoNormal">How about Wednesday afternoon? I have '
        "2pm-4pm open.</p>\r\n"
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        '<p class="MsoNormal">Priya</p>\r\n'
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        "<!-- === QUOTED: message 1 (original) === -->\r\n"
        '<div id="divRplyFwdMsg" dir="ltr">\r\n'
        '<hr style="display:inline-block;width:98%" tabindex="-1">\r\n'
        '<font face="Calibri, sans-serif" style="font-size:11pt"'
        ' color="#000000">'
        "<b>From:</b> Alex Chen &lt;alex.chen@example.com&gt;<br>\r\n"
        "<b>Sent:</b> Tuesday, April 7, 2026 9:05 AM<br>\r\n"
        "<b>To:</b> Priya Patel &lt;priya.patel@example.com&gt;<br>\r\n"
        "<b>Subject:</b> RE: Q2 Planning Session</font>\r\n"
        "</div>\r\n"
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        '<p class="MsoNormal">Priya,</p>\r\n'
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        '<p class="MsoNormal">We need to schedule the Q2 planning session.'
        " What times work for you this week?</p>\r\n"
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        '<p class="MsoNormal">Thanks,</p>\r\n'
        '<p class="MsoNormal">Alex</p>\r\n'
        "</div>\r\n"
        "</body>\r\n"
        "</html>"
    ),
    "text": (
        "Perfect, Wednesday at 2pm works for me. I'll book the conference room.\r\n"
        "\r\n"
        "- Alex\r\n"
        "\r\n"
        "-----Original Message-----\r\n"
        "From: Priya Patel <priya.patel@example.com>\r\n"
        "Sent: Tuesday, April 7, 2026 11:30 AM\r\n"
        "To: Alex Chen <alex.chen@example.com>\r\n"
        "Subject: RE: RE: Q2 Planning Session\r\n"
        "\r\n"
        "Hi Alex,\r\n"
        "\r\n"
        "How about Wednesday afternoon? I have 2pm-4pm open.\r\n"
        "\r\n"
        "Priya\r\n"
        "\r\n"
        "-----Original Message-----\r\n"
        "From: Alex Chen <alex.chen@example.com>\r\n"
        "Sent: Tuesday, April 7, 2026 9:05 AM\r\n"
        "To: Priya Patel <priya.patel@example.com>\r\n"
        "Subject: RE: Q2 Planning Session\r\n"
        "\r\n"
        "Priya,\r\n"
        "\r\n"
        "We need to schedule the Q2 planning session."
        " What times work for you this week?\r\n"
        "\r\n"
        "Thanks,\r\n"
        "Alex\r\n"
    ),
    "expected_reply": (
        "Perfect, Wednesday at 2pm works for me. I'll book the conference room.\n"
        "\n"
        "- Alex"
    ),
    "expected_quoted": (
        "Hi Alex,\n"
        "\n"
        "How about Wednesday afternoon? I have 2pm-4pm open.\n"
        "\n"
        "Priya\n"
        "\n"
        "Priya,\n"
        "\n"
        "We need to schedule the Q2 planning session."
        " What times work for you this week?\n"
        "\n"
        "Thanks,\n"
        "Alex"
    ),
    "has_identifier_in_quote_only": False,
}


# ---------------------------------------------------------------------------
# 4. Outlook forwarded message
# ---------------------------------------------------------------------------
OUTLOOK_FORWARDED = {
    "name": "outlook_forwarded_message",
    "html": (
        '<html xmlns:v="urn:schemas-microsoft-com:vml"'
        ' xmlns:o="urn:schemas-microsoft-com:office:office"'
        ' xmlns="http://www.w3.org/TR/REC-html40">\r\n'
        "<head>\r\n"
        '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">\r\n'
        '<meta name="Generator" content="Microsoft Word 15 (filtered medium)">\r\n'
        "<style><!--\r\n"
        "p.MsoNormal, li.MsoNormal, div.MsoNormal {\r\n"
        "  margin: 0in;\r\n"
        "  font-size: 11.0pt;\r\n"
        '  font-family: "Calibri", sans-serif;\r\n'
        "}\r\n"
        "--></style>\r\n"
        "</head>\r\n"
        '<body lang="EN-US" link="#0563C1" vlink="#954F72"'
        ' style="word-wrap:break-word">\r\n'
        '<div class="WordSection1">\r\n'
        '<p class="MsoNormal">FYI -- see the server alert below. '
        "Can you take a look?</p>\r\n"
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        '<p class="MsoNormal">Thanks,</p>\r\n'
        '<p class="MsoNormal">Mike</p>\r\n'
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        '<div id="divRplyFwdMsg" dir="ltr">\r\n'
        '<hr style="display:inline-block;width:98%" tabindex="-1">\r\n'
        '<font face="Calibri, sans-serif" style="font-size:11pt"'
        ' color="#000000">'
        "<b>From:</b> Monitoring System &lt;alerts@infra.example.com&gt;<br>\r\n"
        "<b>Sent:</b> Thursday, April 10, 2026 2:17 AM<br>\r\n"
        "<b>To:</b> Mike Torres &lt;mike.torres@example.com&gt;<br>\r\n"
        "<b>Subject:</b> [ALERT] High CPU on prod-web-03</font>\r\n"
        "</div>\r\n"
        '<div style="border:none;border-top:solid #E1E1E1 1.0pt;'
        'padding:3.0pt 0in 0in 0in">\r\n'
        '<p class="MsoNormal">&nbsp;</p>\r\n'
        "</div>\r\n"
        '<p class="MsoNormal" style="margin-bottom:12.0pt">'
        '<span style="font-family:Consolas;font-size:10.0pt">'
        "ALERT: CPU utilization on prod-web-03 exceeded 95% "
        "for 15 consecutive minutes.<br>\r\n"
        "Timestamp: 2026-04-10T02:17:04Z<br>\r\n"
        "Current load average: 47.2, 42.8, 38.1<br>\r\n"
        "Top process: java (PID 14923) -- 89.3% CPU<br>\r\n"
        "<br>\r\n"
        "Acknowledge this alert: https://monitoring.example.com/alert/88412"
        "</span></p>\r\n"
        "</div>\r\n"
        "</body>\r\n"
        "</html>"
    ),
    "text": (
        "FYI -- see the server alert below. Can you take a look?\r\n"
        "\r\n"
        "Thanks,\r\n"
        "Mike\r\n"
        "\r\n"
        "-----Original Message-----\r\n"
        "From: Monitoring System <alerts@infra.example.com>\r\n"
        "Sent: Thursday, April 10, 2026 2:17 AM\r\n"
        "To: Mike Torres <mike.torres@example.com>\r\n"
        "Subject: [ALERT] High CPU on prod-web-03\r\n"
        "\r\n"
        "ALERT: CPU utilization on prod-web-03 exceeded 95% "
        "for 15 consecutive minutes.\r\n"
        "Timestamp: 2026-04-10T02:17:04Z\r\n"
        "Current load average: 47.2, 42.8, 38.1\r\n"
        "Top process: java (PID 14923) -- 89.3% CPU\r\n"
        "\r\n"
        "Acknowledge this alert: https://monitoring.example.com/alert/88412\r\n"
    ),
    "expected_reply": (
        "FYI -- see the server alert below. Can you take a look?\n"
        "\n"
        "Thanks,\n"
        "Mike"
    ),
    "expected_quoted": (
        "ALERT: CPU utilization on prod-web-03 exceeded 95% "
        "for 15 consecutive minutes.\n"
        "Timestamp: 2026-04-10T02:17:04Z\n"
        "Current load average: 47.2, 42.8, 38.1\n"
        "Top process: java (PID 14923) -- 89.3% CPU\n"
        "\n"
        "Acknowledge this alert: https://monitoring.example.com/alert/88412"
    ),
    "has_identifier_in_quote_only": False,
}


# ---------------------------------------------------------------------------
# 5. Gmail reply with gmail_quote div
# ---------------------------------------------------------------------------
GMAIL_REPLY = {
    "name": "gmail_reply_with_gmail_quote",
    "html": (
        '<div dir="ltr">'
        '<div dir="ltr">'
        "<div>Hey team,</div>"
        "<div><br></div>"
        "<div>I reviewed the PR and left a few comments. The main issue is"
        " the N+1 query in the user listing endpoint -- we should batch"
        " those lookups.</div>"
        "<div><br></div>"
        "<div>Otherwise LGTM!</div>"
        "<div><br></div>"
        "<div>- Dana</div>"
        "</div>"
        "</div>"
        '<br>'
        '<div class="gmail_quote">'
        '<div dir="ltr" class="gmail_attr">'
        "On Wed, Apr 8, 2026 at 4:22\u202fPM Tom Wilson"
        " &lt;<a href=\"mailto:tom.wilson@example.com\""
        ">tom.wilson@example.com</a>&gt; wrote:<br>"
        "</div>"
        '<blockquote class="gmail_quote"'
        ' style="margin:0px 0px 0px 0.8ex;'
        "border-left:1px solid rgb(204,204,204);"
        'padding-left:1ex">'
        '<div dir="ltr">'
        "<div>Hi all,</div>"
        "<div><br></div>"
        "<div>PR #1847 is ready for review:</div>"
        "<div><a href=\"https://github.com/example/repo/pull/1847\""
        " target=\"_blank\">"
        "https://github.com/example/repo/pull/1847</a></div>"
        "<div><br></div>"
        "<div>Changes:</div>"
        "<div>- Added pagination to /api/users endpoint</div>"
        "<div>- Updated OpenAPI spec</div>"
        "<div>- Added integration tests</div>"
        "<div><br></div>"
        "<div>Thanks,</div>"
        "<div>Tom</div>"
        "</div>"
        "</blockquote>"
        "</div>"
    ),
    "text": (
        "Hey team,\r\n"
        "\r\n"
        "I reviewed the PR and left a few comments. The main issue is"
        " the N+1 query in the user listing endpoint -- we should batch"
        " those lookups.\r\n"
        "\r\n"
        "Otherwise LGTM!\r\n"
        "\r\n"
        "- Dana\r\n"
        "\r\n"
        "On Wed, Apr 8, 2026 at 4:22 PM Tom Wilson"
        " <tom.wilson@example.com> wrote:\r\n"
        ">\r\n"
        "> Hi all,\r\n"
        ">\r\n"
        "> PR #1847 is ready for review:\r\n"
        "> https://github.com/example/repo/pull/1847\r\n"
        ">\r\n"
        "> Changes:\r\n"
        "> - Added pagination to /api/users endpoint\r\n"
        "> - Updated OpenAPI spec\r\n"
        "> - Added integration tests\r\n"
        ">\r\n"
        "> Thanks,\r\n"
        "> Tom\r\n"
    ),
    "expected_reply": (
        "Hey team,\n"
        "\n"
        "I reviewed the PR and left a few comments. The main issue is"
        " the N+1 query in the user listing endpoint -- we should batch"
        " those lookups.\n"
        "\n"
        "Otherwise LGTM!\n"
        "\n"
        "- Dana"
    ),
    "expected_quoted": (
        "Hi all,\n"
        "\n"
        "PR #1847 is ready for review:\n"
        "https://github.com/example/repo/pull/1847\n"
        "\n"
        "Changes:\n"
        "- Added pagination to /api/users endpoint\n"
        "- Updated OpenAPI spec\n"
        "- Added integration tests\n"
        "\n"
        "Thanks,\n"
        "Tom"
    ),
    "has_identifier_in_quote_only": False,
}


# ---------------------------------------------------------------------------
# 6. Gmail forwarded message
# ---------------------------------------------------------------------------
GMAIL_FORWARDED = {
    "name": "gmail_forwarded_message",
    "html": (
        '<div dir="ltr">'
        '<div dir="ltr">'
        "<div>Forwarding this for visibility -- the vendor confirmed"
        " the new pricing below.</div>"
        "<div><br></div>"
        "<div>- Rachel</div>"
        "</div>"
        "<br>"
        '<div class="gmail_quote">'
        '<div dir="ltr" class="gmail_attr">'
        "---------- Forwarded message ---------<br>"
        "From: <b class=\"gmail_sendername\" dir=\"auto\">"
        "CloudVendor Sales</b>"
        " <span dir=\"auto\">"
        "&lt;<a href=\"mailto:sales@cloudvendor.example.com\">"
        "sales@cloudvendor.example.com</a>&gt;</span><br>"
        "Date: Mon, Apr 6, 2026 at 10:03\u202fAM<br>"
        "Subject: Re: Enterprise License Renewal<br>"
        "To: Rachel Kim &lt;<a href=\"mailto:rachel.kim@example.com\">"
        "rachel.kim@example.com</a>&gt;<br>"
        "</div>"
        "<br><br>"
        '<blockquote class="gmail_quote"'
        ' style="margin:0px 0px 0px 0.8ex;'
        "border-left:1px solid rgb(204,204,204);"
        'padding-left:1ex">'
        '<div dir="ltr">'
        "<div>Hi Rachel,</div>"
        "<div><br></div>"
        "<div>Thank you for your continued partnership. Here is the"
        " updated pricing for your renewal:</div>"
        "<div><br></div>"
        "<div><b>Enterprise Plan (500 seats)</b></div>"
        "<div>Annual: $124,500 (was $118,000)</div>"
        "<div>Multi-year (3yr): $112,050/year</div>"
        "<div><br></div>"
        "<div>This quote is valid until April 30, 2026.</div>"
        "<div><br></div>"
        "<div>Best regards,</div>"
        "<div>James Morton</div>"
        "<div>CloudVendor Enterprise Sales</div>"
        "</div>"
        "</blockquote>"
        "</div>"
        "</div>"
    ),
    "text": (
        "Forwarding this for visibility -- the vendor confirmed"
        " the new pricing below.\r\n"
        "\r\n"
        "- Rachel\r\n"
        "\r\n"
        "---------- Forwarded message ---------\r\n"
        "From: CloudVendor Sales <sales@cloudvendor.example.com>\r\n"
        "Date: Mon, Apr 6, 2026 at 10:03 AM\r\n"
        "Subject: Re: Enterprise License Renewal\r\n"
        "To: Rachel Kim <rachel.kim@example.com>\r\n"
        "\r\n"
        "Hi Rachel,\r\n"
        "\r\n"
        "Thank you for your continued partnership. Here is the"
        " updated pricing for your renewal:\r\n"
        "\r\n"
        "Enterprise Plan (500 seats)\r\n"
        "Annual: $124,500 (was $118,000)\r\n"
        "Multi-year (3yr): $112,050/year\r\n"
        "\r\n"
        "This quote is valid until April 30, 2026.\r\n"
        "\r\n"
        "Best regards,\r\n"
        "James Morton\r\n"
        "CloudVendor Enterprise Sales\r\n"
    ),
    "expected_reply": (
        "Forwarding this for visibility -- the vendor confirmed"
        " the new pricing below.\n"
        "\n"
        "- Rachel"
    ),
    "expected_quoted": (
        "Hi Rachel,\n"
        "\n"
        "Thank you for your continued partnership. Here is the"
        " updated pricing for your renewal:\n"
        "\n"
        "Enterprise Plan (500 seats)\n"
        "Annual: $124,500 (was $118,000)\n"
        "Multi-year (3yr): $112,050/year\n"
        "\n"
        "This quote is valid until April 30, 2026.\n"
        "\n"
        "Best regards,\n"
        "James Morton\n"
        "CloudVendor Enterprise Sales"
    ),
    "has_identifier_in_quote_only": False,
}


# ---------------------------------------------------------------------------
# 7. Apple Mail reply with blockquote type="cite"
# ---------------------------------------------------------------------------
APPLE_MAIL_REPLY = {
    "name": "apple_mail_reply_blockquote_cite",
    "html": (
        "<html>\r\n"
        "<head>\r\n"
        '<meta http-equiv="Content-Type"'
        ' content="text/html; charset=utf-8">\r\n'
        "</head>\r\n"
        "<body"
        ' style="word-wrap: break-word;'
        " -webkit-nbsp-mode: space;"
        ' line-break: after-white-space;">\r\n'
        "<div>Sounds great, I'll pick up the tickets. See you there!</div>"
        "<div><br></div>"
        "<div>Cheers,</div>"
        "<div>Liam</div>"
        "<div><br></div>"
        '<div><br>'
        '<blockquote type="cite">'
        "<div>On Apr 9, 2026, at 6:45 PM, Nora Fischer"
        " &lt;<a href=\"mailto:nora.fischer@example.com\">"
        "nora.fischer@example.com</a>&gt; wrote:</div>"
        "<br>"
        '<div>'
        '<div style="word-wrap: break-word;'
        " -webkit-nbsp-mode: space;"
        ' line-break: after-white-space;">'
        "<div>Hey Liam,</div>"
        "<div><br></div>"
        "<div>Want to catch the new exhibit at the Modern Art Museum"
        " this Saturday? They have a Basquiat retrospective that"
        " closes next week.</div>"
        "<div><br></div>"
        "<div>I was thinking the 2pm slot so we can grab coffee"
        " after.</div>"
        "<div><br></div>"
        "<div>Let me know!</div>"
        "<div>Nora</div>"
        '<div><br></div>'
        '<div>'
        '<div style="'
        "border-top: 1px solid rgb(179, 179, 179);"
        " border-bottom: 1px solid rgb(179, 179, 179);"
        " background: rgb(245, 245, 245);"
        " padding: 8px;"
        '">'
        '<div style="font: 11px Menlo; color: rgb(0,0,0)">'
        "Sent from my iPhone"
        "</div>"
        "</div>"
        "</div>"
        "</div>"
        "</div>"
        "</blockquote>"
        "</div>\r\n"
        "</body>\r\n"
        "</html>"
    ),
    "text": (
        "Sounds great, I'll pick up the tickets. See you there!\r\n"
        "\r\n"
        "Cheers,\r\n"
        "Liam\r\n"
        "\r\n"
        "> On Apr 9, 2026, at 6:45 PM, Nora Fischer"
        " <nora.fischer@example.com> wrote:\r\n"
        "> \r\n"
        "> Hey Liam,\r\n"
        "> \r\n"
        "> Want to catch the new exhibit at the Modern Art Museum"
        " this Saturday? They have a Basquiat retrospective that"
        " closes next week.\r\n"
        "> \r\n"
        "> I was thinking the 2pm slot so we can grab coffee after.\r\n"
        "> \r\n"
        "> Let me know!\r\n"
        "> Nora\r\n"
        "> \r\n"
        "> Sent from my iPhone\r\n"
    ),
    "expected_reply": (
        "Sounds great, I'll pick up the tickets. See you there!\n"
        "\n"
        "Cheers,\n"
        "Liam"
    ),
    "expected_quoted": (
        "Hey Liam,\n"
        "\n"
        "Want to catch the new exhibit at the Modern Art Museum"
        " this Saturday? They have a Basquiat retrospective that"
        " closes next week.\n"
        "\n"
        "I was thinking the 2pm slot so we can grab coffee after.\n"
        "\n"
        "Let me know!\n"
        "Nora"
    ),
    "has_identifier_in_quote_only": False,
}


# ---------------------------------------------------------------------------
# 8. Plain text: simple top-posted reply with "On [date] wrote:" + > prefixes
# ---------------------------------------------------------------------------
PLAIN_TEXT_TOP_POST = {
    "name": "plain_text_top_posted_reply",
    "html": None,
    "text": (
        "Yep, the fix is deployed. Latency is back to normal.\r\n"
        "\r\n"
        "- Kevin\r\n"
        "\r\n"
        "On Wed, Apr 8, 2026 at 7:13 PM Lisa Park"
        " <lisa.park@example.com> wrote:\r\n"
        "> Hey Kevin,\r\n"
        ">\r\n"
        "> Did you get a chance to push the hotfix for the latency\r\n"
        "> spike? The SLA dashboard is still showing red.\r\n"
        ">\r\n"
        "> Thanks,\r\n"
        "> Lisa\r\n"
    ),
    "expected_reply": (
        "Yep, the fix is deployed. Latency is back to normal.\n"
        "\n"
        "- Kevin"
    ),
    "expected_quoted": (
        "Hey Kevin,\n"
        "\n"
        "Did you get a chance to push the hotfix for the latency\n"
        "spike? The SLA dashboard is still showing red.\n"
        "\n"
        "Thanks,\n"
        "Lisa"
    ),
    "has_identifier_in_quote_only": False,
}


# ---------------------------------------------------------------------------
# 9. Plain text with "-----Original Message-----" (Outlook plain text)
# ---------------------------------------------------------------------------
PLAIN_TEXT_OUTLOOK_ORIGINAL_MSG = {
    "name": "plain_text_outlook_original_message_separator",
    "html": None,
    "text": (
        "Confirmed -- I'll add it to the sprint backlog.\r\n"
        "\r\n"
        "Regards,\r\n"
        "Brian\r\n"
        "\r\n"
        "-----Original Message-----\r\n"
        "From: Chloe Adams [mailto:chloe.adams@example.com]\r\n"
        "Sent: Monday, April 6, 2026 4:55 PM\r\n"
        "To: Brian Lee <brian.lee@example.com>\r\n"
        "Subject: Bug Report: Login page 500 error\r\n"
        "\r\n"
        "Hi Brian,\r\n"
        "\r\n"
        "Users are reporting intermittent 500 errors on the login page.\r\n"
        "It started around 3pm today. The error rate is about 12% of\r\n"
        "requests according to Datadog.\r\n"
        "\r\n"
        "Stack trace points to the session middleware:\r\n"
        "\r\n"
        "  SessionStore.get() -> Redis connection timeout\r\n"
        "  at middleware/session.js:47\r\n"
        "  at async Router.handle()\r\n"
        "\r\n"
        "Can you prioritize this?\r\n"
        "\r\n"
        "Thanks,\r\n"
        "Chloe\r\n"
    ),
    "expected_reply": (
        "Confirmed -- I'll add it to the sprint backlog.\n"
        "\n"
        "Regards,\n"
        "Brian"
    ),
    "expected_quoted": (
        "Hi Brian,\n"
        "\n"
        "Users are reporting intermittent 500 errors on the login page.\n"
        "It started around 3pm today. The error rate is about 12% of\n"
        "requests according to Datadog.\n"
        "\n"
        "Stack trace points to the session middleware:\n"
        "\n"
        "  SessionStore.get() -> Redis connection timeout\n"
        "  at middleware/session.js:47\n"
        "  at async Router.handle()\n"
        "\n"
        "Can you prioritize this?\n"
        "\n"
        "Thanks,\n"
        "Chloe"
    ),
    "has_identifier_in_quote_only": False,
}


# ---------------------------------------------------------------------------
# 10. Non-English: German reply with "Am [date] schrieb [person]:"
# ---------------------------------------------------------------------------
GERMAN_REPLY = {
    "name": "german_reply_am_schrieb",
    "html": (
        '<div dir="ltr">'
        '<div dir="ltr">'
        "<div>Hallo Max,</div>"
        "<div><br></div>"
        "<div>Ja, der Termin passt mir. Ich bringe die "
        "Pr\u00e4sentation mit.</div>"
        "<div><br></div>"
        "<div>Viele Gr\u00fc\u00dfe,</div>"
        "<div>Sabine</div>"
        "</div>"
        "</div>"
        '<br>'
        '<div class="gmail_quote">'
        '<div dir="ltr" class="gmail_attr">'
        "Am Di., 7. Apr. 2026 um 14:30 Uhr schrieb Max M\u00fcller"
        " &lt;<a href=\"mailto:max.mueller@beispiel.de\">"
        "max.mueller@beispiel.de</a>&gt;:<br>"
        "</div>"
        '<blockquote class="gmail_quote"'
        ' style="margin:0px 0px 0px 0.8ex;'
        "border-left:1px solid rgb(204,204,204);"
        'padding-left:1ex">'
        '<div dir="ltr">'
        "<div>Hallo Sabine,</div>"
        "<div><br></div>"
        "<div>K\u00f6nnen wir morgen um 10 Uhr das Projekt besprechen?"
        " Ich habe den Besprechungsraum 3B reserviert.</div>"
        "<div><br></div>"
        "<div>Gru\u00df,</div>"
        "<div>Max</div>"
        "</div>"
        "</blockquote>"
        "</div>"
    ),
    "text": (
        "Hallo Max,\r\n"
        "\r\n"
        "Ja, der Termin passt mir. Ich bringe die"
        " Pr\u00e4sentation mit.\r\n"
        "\r\n"
        "Viele Gr\u00fc\u00dfe,\r\n"
        "Sabine\r\n"
        "\r\n"
        "Am Di., 7. Apr. 2026 um 14:30 Uhr schrieb Max M\u00fcller"
        " <max.mueller@beispiel.de>:\r\n"
        "> Hallo Sabine,\r\n"
        ">\r\n"
        "> K\u00f6nnen wir morgen um 10 Uhr das Projekt besprechen?"
        " Ich habe den Besprechungsraum 3B reserviert.\r\n"
        ">\r\n"
        "> Gru\u00df,\r\n"
        "> Max\r\n"
    ),
    "expected_reply": (
        "Hallo Max,\n"
        "\n"
        "Ja, der Termin passt mir. Ich bringe die"
        " Pr\u00e4sentation mit.\n"
        "\n"
        "Viele Gr\u00fc\u00dfe,\n"
        "Sabine"
    ),
    "expected_quoted": (
        "Hallo Sabine,\n"
        "\n"
        "K\u00f6nnen wir morgen um 10 Uhr das Projekt besprechen?"
        " Ich habe den Besprechungsraum 3B reserviert.\n"
        "\n"
        "Gru\u00df,\n"
        "Max"
    ),
    "has_identifier_in_quote_only": False,
}


# ---------------------------------------------------------------------------
# 11. Fresh message -- no quoted content at all
# ---------------------------------------------------------------------------
FRESH_MESSAGE_NO_QUOTE = {
    "name": "fresh_message_no_quoted_content",
    "html": (
        '<html>\r\n'
        '<head>\r\n'
        '<meta http-equiv="Content-Type"'
        ' content="text/html; charset=UTF-8">\r\n'
        '</head>\r\n'
        '<body>\r\n'
        '<div dir="ltr">'
        "<div>Hi everyone,</div>"
        "<div><br></div>"
        "<div>Just a reminder that the office will be closed this Friday"
        " for the company retreat. Please make sure all critical PRs"
        " are merged by Thursday EOD.</div>"
        "<div><br></div>"
        "<div>Location: Riverside Conference Center, Building A</div>"
        "<div>Time: 9am - 5pm</div>"
        "<div>Lunch will be provided.</div>"
        "<div><br></div>"
        "<div>See you there!</div>"
        "<div>Emma</div>"
        "</div>\r\n"
        "</body>\r\n"
        "</html>"
    ),
    "text": (
        "Hi everyone,\r\n"
        "\r\n"
        "Just a reminder that the office will be closed this Friday"
        " for the company retreat. Please make sure all critical PRs"
        " are merged by Thursday EOD.\r\n"
        "\r\n"
        "Location: Riverside Conference Center, Building A\r\n"
        "Time: 9am - 5pm\r\n"
        "Lunch will be provided.\r\n"
        "\r\n"
        "See you there!\r\n"
        "Emma\r\n"
    ),
    "expected_reply": (
        "Hi everyone,\n"
        "\n"
        "Just a reminder that the office will be closed this Friday"
        " for the company retreat. Please make sure all critical PRs"
        " are merged by Thursday EOD.\n"
        "\n"
        "Location: Riverside Conference Center, Building A\n"
        "Time: 9am - 5pm\n"
        "Lunch will be provided.\n"
        "\n"
        "See you there!\n"
        "Emma"
    ),
    "expected_quoted": None,
    "has_identifier_in_quote_only": False,
}


# ---------------------------------------------------------------------------
# 12. Email with only a signature and legal disclaimer, no quoted content
# ---------------------------------------------------------------------------
SIGNATURE_AND_DISCLAIMER_ONLY = {
    "name": "signature_and_legal_disclaimer_no_quote",
    "html": (
        '<html>\r\n'
        '<head>\r\n'
        '<meta http-equiv="Content-Type"'
        ' content="text/html; charset=UTF-8">\r\n'
        '</head>\r\n'
        '<body>\r\n'
        '<div dir="ltr">'
        "<div>Please find the Q1 financial report attached.</div>"
        "<div><br></div>"
        "</div>\r\n"
        "<!-- Signature -->\r\n"
        '<div style="font-size:9pt;font-family:Arial,sans-serif;'
        'color:#666666;">\r\n'
        "<p><b>Jennifer Wu</b><br>\r\n"
        "Senior Financial Analyst<br>\r\n"
        "Acme Corporation<br>\r\n"
        "Tel: +1 (555) 234-5678<br>\r\n"
        '<a href="mailto:jennifer.wu@acme.example.com"'
        ' style="color:#0563C1;">'
        "jennifer.wu@acme.example.com</a></p>\r\n"
        "</div>\r\n"
        '<div style="font-size:7pt;font-family:Arial,sans-serif;'
        'color:#999999;border-top:1px solid #cccccc;'
        'padding-top:8px;margin-top:16px;">\r\n'
        "<p>CONFIDENTIALITY NOTICE: This e-mail message, including any"
        " attachments, is for the sole use of the intended recipient(s)"
        " and may contain confidential and privileged information."
        " Any unauthorized review, use, disclosure, or distribution"
        " is prohibited. If you are not the intended recipient,"
        " please contact the sender by reply e-mail and destroy all"
        " copies of the original message. Thank you.</p>\r\n"
        "</div>\r\n"
        "</body>\r\n"
        "</html>"
    ),
    "text": (
        "Please find the Q1 financial report attached.\r\n"
        "\r\n"
        "--\r\n"
        "Jennifer Wu\r\n"
        "Senior Financial Analyst\r\n"
        "Acme Corporation\r\n"
        "Tel: +1 (555) 234-5678\r\n"
        "jennifer.wu@acme.example.com\r\n"
        "\r\n"
        "CONFIDENTIALITY NOTICE: This e-mail message, including any"
        " attachments, is for the sole use of the intended recipient(s)"
        " and may contain confidential and privileged information."
        " Any unauthorized review, use, disclosure, or distribution"
        " is prohibited. If you are not the intended recipient,"
        " please contact the sender by reply e-mail and destroy all"
        " copies of the original message. Thank you.\r\n"
    ),
    "expected_reply": (
        "Please find the Q1 financial report attached."
    ),
    "expected_quoted": None,
    "has_identifier_in_quote_only": False,
}


# ---------------------------------------------------------------------------
# 13. Reply with inline/interleaved quoting
# ---------------------------------------------------------------------------
INLINE_INTERLEAVED_QUOTING = {
    "name": "inline_interleaved_quoting",
    "html": None,
    "text": (
        "Answers inline below.\r\n"
        "\r\n"
        "On Mon, Apr 6, 2026 at 2:00 PM, Product Team"
        " <product@example.com> wrote:\r\n"
        "> 1. Should we support CSV export in v1?\r\n"
        "\r\n"
        "Yes, CSV export is a must-have. Our top 3 enterprise"
        " customers have explicitly asked for it.\r\n"
        "\r\n"
        "> 2. What's the target date for the beta launch?\r\n"
        "\r\n"
        "May 15th. We have some buffer built in but I'd rather"
        " not slip past that.\r\n"
        "\r\n"
        "> 3. Do we need SSO for the beta, or can that wait for GA?\r\n"
        "\r\n"
        "SSO can wait for GA. None of the beta participants require"
        " it per their contracts.\r\n"
        "\r\n"
        "> 4. Budget status?\r\n"
        "\r\n"
        "We're at 73% of the allocated budget with 60% of the work"
        " complete. Should be fine.\r\n"
        "\r\n"
        "Let me know if there are follow-up questions.\r\n"
        "\r\n"
        "- Raj\r\n"
    ),
    "expected_reply": (
        "Answers inline below.\n"
        "\n"
        "Yes, CSV export is a must-have. Our top 3 enterprise"
        " customers have explicitly asked for it.\n"
        "\n"
        "May 15th. We have some buffer built in but I'd rather"
        " not slip past that.\n"
        "\n"
        "SSO can wait for GA. None of the beta participants require"
        " it per their contracts.\n"
        "\n"
        "We're at 73% of the allocated budget with 60% of the work"
        " complete. Should be fine.\n"
        "\n"
        "Let me know if there are follow-up questions.\n"
        "\n"
        "- Raj"
    ),
    "expected_quoted": (
        "1. Should we support CSV export in v1?\n"
        "\n"
        "2. What's the target date for the beta launch?\n"
        "\n"
        "3. Do we need SSO for the beta, or can that wait for GA?\n"
        "\n"
        "4. Budget status?"
    ),
    "has_identifier_in_quote_only": False,
}


# ---------------------------------------------------------------------------
# 14. Forward without any new text added (entirely quoted)
# ---------------------------------------------------------------------------
FORWARD_NO_NEW_TEXT = {
    "name": "forward_without_new_text_entirely_quoted",
    "html": (
        '<div dir="ltr">'
        '<br>'
        '<div class="gmail_quote">'
        '<div dir="ltr" class="gmail_attr">'
        "---------- Forwarded message ---------<br>"
        "From: <b class=\"gmail_sendername\" dir=\"auto\">"
        "CI Bot</b>"
        " <span dir=\"auto\">"
        "&lt;<a href=\"mailto:ci@builds.example.com\">"
        "ci@builds.example.com</a>&gt;</span><br>"
        "Date: Thu, Apr 10, 2026 at 1:42\u202fAM<br>"
        "Subject: [BUILD FAILED] main - commit abc1234<br>"
        "To: dev-alerts &lt;<a href=\"mailto:dev-alerts@example.com\">"
        "dev-alerts@example.com</a>&gt;<br>"
        "</div>"
        "<br><br>"
        '<blockquote class="gmail_quote"'
        ' style="margin:0px 0px 0px 0.8ex;'
        "border-left:1px solid rgb(204,204,204);"
        'padding-left:1ex">'
        '<div dir="ltr">'
        "<div><b>Build Status: FAILED</b></div>"
        "<div><br></div>"
        "<div>Branch: main</div>"
        "<div>Commit: abc1234 - \"Fix user serialization\"</div>"
        "<div>Author: dev3@example.com</div>"
        "<div><br></div>"
        "<div>Failed step: test-integration (exit code 1)</div>"
        "<div><br></div>"
        "<div><pre style=\"font-family:monospace;font-size:10pt;"
        'background:#f5f5f5;padding:8px;">'
        "FAIL tests/integration/test_user_api.py::test_create_user\n"
        "  AssertionError: Expected status 201, got 500\n"
        "  Response body: {\"error\": \"column \\\"email\\\" violates"
        " not-null constraint\"}\n"
        "\n"
        "1 failed, 47 passed, 2 skipped in 34.21s"
        "</pre></div>"
        "<div><br></div>"
        "<div><a href=\"https://ci.example.com/builds/99817\">"
        "View full build log</a></div>"
        "</div>"
        "</blockquote>"
        "</div>"
        "</div>"
    ),
    "text": (
        "\r\n"
        "---------- Forwarded message ---------\r\n"
        "From: CI Bot <ci@builds.example.com>\r\n"
        "Date: Thu, Apr 10, 2026 at 1:42 AM\r\n"
        "Subject: [BUILD FAILED] main - commit abc1234\r\n"
        "To: dev-alerts <dev-alerts@example.com>\r\n"
        "\r\n"
        "Build Status: FAILED\r\n"
        "\r\n"
        "Branch: main\r\n"
        "Commit: abc1234 - \"Fix user serialization\"\r\n"
        "Author: dev3@example.com\r\n"
        "\r\n"
        "Failed step: test-integration (exit code 1)\r\n"
        "\r\n"
        "FAIL tests/integration/test_user_api.py::test_create_user\r\n"
        "  AssertionError: Expected status 201, got 500\r\n"
        "  Response body: {\"error\": \"column \\\"email\\\" violates"
        " not-null constraint\"}\r\n"
        "\r\n"
        "1 failed, 47 passed, 2 skipped in 34.21s\r\n"
        "\r\n"
        "View full build log: https://ci.example.com/builds/99817\r\n"
    ),
    "expected_reply": "",
    "expected_quoted": (
        "Build Status: FAILED\n"
        "\n"
        "Branch: main\n"
        "Commit: abc1234 - \"Fix user serialization\"\n"
        "Author: dev3@example.com\n"
        "\n"
        "Failed step: test-integration (exit code 1)\n"
        "\n"
        "FAIL tests/integration/test_user_api.py::test_create_user\n"
        "  AssertionError: Expected status 201, got 500\n"
        "  Response body: {\"error\": \"column \\\"email\\\" violates"
        " not-null constraint\"}\n"
        "\n"
        "1 failed, 47 passed, 2 skipped in 34.21s\n"
        "\n"
        "View full build log: https://ci.example.com/builds/99817"
    ),
    "has_identifier_in_quote_only": False,
}


# ---------------------------------------------------------------------------
# 15. Identifier "1234-2026" appears in the quoted section but NOT in the
#     new reply -- tests that a parser correctly extracts from the new
#     content only
# ---------------------------------------------------------------------------
IDENTIFIER_IN_QUOTE_ONLY = {
    "name": "identifier_1234_2026_in_quote_only",
    "html": (
        '<div dir="ltr">'
        '<div dir="ltr">'
        "<div>Thanks for flagging this. I've reassigned the ticket to"
        " the backend team -- they should have a fix out today.</div>"
        "<div><br></div>"
        "<div>Best,</div>"
        "<div>Tanya</div>"
        "</div>"
        "</div>"
        '<br>'
        '<div class="gmail_quote">'
        '<div dir="ltr" class="gmail_attr">'
        "On Tue, Apr 7, 2026 at 11:05\u202fAM Omar Hassan"
        " &lt;<a href=\"mailto:omar.hassan@example.com\">"
        "omar.hassan@example.com</a>&gt; wrote:<br>"
        "</div>"
        '<blockquote class="gmail_quote"'
        ' style="margin:0px 0px 0px 0.8ex;'
        "border-left:1px solid rgb(204,204,204);"
        'padding-left:1ex">'
        '<div dir="ltr">'
        "<div>Hi Tanya,</div>"
        "<div><br></div>"
        "<div>Ticket 1234-2026 is showing a regression in the payment"
        " processing module. Customers in the EU region are getting"
        " a \"currency not supported\" error even for EUR"
        " transactions.</div>"
        "<div><br></div>"
        "<div>Steps to reproduce:</div>"
        "<div>1. Log in as an EU customer</div>"
        "<div>2. Add items to cart totaling over \u20ac50</div>"
        "<div>3. Proceed to checkout with a Visa card</div>"
        "<div>4. Observe the error on the payment confirmation"
        " page</div>"
        "<div><br></div>"
        "<div>This is blocking several orders. Ref: 1234-2026</div>"
        "<div><br></div>"
        "<div>Thanks,</div>"
        "<div>Omar</div>"
        "</div>"
        "</blockquote>"
        "</div>"
    ),
    "text": (
        "Thanks for flagging this. I've reassigned the ticket to"
        " the backend team -- they should have a fix out today.\r\n"
        "\r\n"
        "Best,\r\n"
        "Tanya\r\n"
        "\r\n"
        "On Tue, Apr 7, 2026 at 11:05 AM Omar Hassan"
        " <omar.hassan@example.com> wrote:\r\n"
        "> Hi Tanya,\r\n"
        ">\r\n"
        "> Ticket 1234-2026 is showing a regression in the payment\r\n"
        "> processing module. Customers in the EU region are getting\r\n"
        "> a \"currency not supported\" error even for EUR\r\n"
        "> transactions.\r\n"
        ">\r\n"
        "> Steps to reproduce:\r\n"
        "> 1. Log in as an EU customer\r\n"
        "> 2. Add items to cart totaling over \u20ac50\r\n"
        "> 3. Proceed to checkout with a Visa card\r\n"
        "> 4. Observe the error on the payment confirmation page\r\n"
        ">\r\n"
        "> This is blocking several orders. Ref: 1234-2026\r\n"
        ">\r\n"
        "> Thanks,\r\n"
        "> Omar\r\n"
    ),
    "expected_reply": (
        "Thanks for flagging this. I've reassigned the ticket to"
        " the backend team -- they should have a fix out today.\n"
        "\n"
        "Best,\n"
        "Tanya"
    ),
    "expected_quoted": (
        "Hi Tanya,\n"
        "\n"
        "Ticket 1234-2026 is showing a regression in the payment\n"
        "processing module. Customers in the EU region are getting\n"
        "a \"currency not supported\" error even for EUR\n"
        "transactions.\n"
        "\n"
        "Steps to reproduce:\n"
        "1. Log in as an EU customer\n"
        "2. Add items to cart totaling over \u20ac50\n"
        "3. Proceed to checkout with a Visa card\n"
        "4. Observe the error on the payment confirmation page\n"
        "\n"
        "This is blocking several orders. Ref: 1234-2026\n"
        "\n"
        "Thanks,\n"
        "Omar"
    ),
    "has_identifier_in_quote_only": True,
}


# ============================================================================
# Aggregate list -- ready for parametrized pytest
# ============================================================================
ALL_FIXTURES = [
    OUTLOOK_DESKTOP_REPLY,           # 1
    OUTLOOK_WEB_APP_REPLY,           # 2
    OUTLOOK_REPLY_CHAIN_DEEP,        # 3
    OUTLOOK_FORWARDED,               # 4
    GMAIL_REPLY,                     # 5
    GMAIL_FORWARDED,                 # 6
    APPLE_MAIL_REPLY,                # 7
    PLAIN_TEXT_TOP_POST,             # 8
    PLAIN_TEXT_OUTLOOK_ORIGINAL_MSG, # 9
    GERMAN_REPLY,                    # 10
    FRESH_MESSAGE_NO_QUOTE,          # 11
    SIGNATURE_AND_DISCLAIMER_ONLY,   # 12
    INLINE_INTERLEAVED_QUOTING,      # 13
    FORWARD_NO_NEW_TEXT,             # 14
    IDENTIFIER_IN_QUOTE_ONLY,        # 15
]

# Convenience subsets for targeted test runs
OUTLOOK_FIXTURES = ALL_FIXTURES[0:4]
GMAIL_FIXTURES = ALL_FIXTURES[4:6]
APPLE_FIXTURES = [ALL_FIXTURES[6]]
PLAIN_TEXT_FIXTURES = ALL_FIXTURES[7:10]
EDGE_CASE_FIXTURES = ALL_FIXTURES[10:15]

# Fixtures that have HTML bodies (for HTML-specific parser tests)
HTML_FIXTURES = [f for f in ALL_FIXTURES if f["html"] is not None]

# Fixtures that have plain text bodies (for text-specific parser tests)
TEXT_FIXTURES = [f for f in ALL_FIXTURES if f["text"] is not None]

# Fixtures that have both HTML and text (for format-preference tests)
DUAL_FORMAT_FIXTURES = [
    f for f in ALL_FIXTURES if f["html"] is not None and f["text"] is not None
]


# ============================================================================
# pytest parametrize helper -- use like:
#
#   from test_fixtures import fixture_params
#
#   @pytest.mark.parametrize("fixture", fixture_params(), ids=fixture_ids())
#   def test_reply_extraction(fixture):
#       result = parse_reply(fixture["html"] or fixture["text"])
#       assert result.strip() == fixture["expected_reply"].strip()
# ============================================================================

def fixture_params(subset=None):
    """Return the fixture list for use with @pytest.mark.parametrize."""
    return subset if subset is not None else ALL_FIXTURES


def fixture_ids(subset=None):
    """Return test IDs matching fixture_params() for readable output."""
    fixtures = subset if subset is not None else ALL_FIXTURES
    return [f["name"] for f in fixtures]
