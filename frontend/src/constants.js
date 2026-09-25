export const LEAD_STATUSES = [
  "New",
  "Contacted",
  "Follow-up",
  "Meeting",
  "Proposal Sent",
  "Successful",
  "Not Interested",
];

export const STATUS_STYLES = {
  New: "bg-slate-100 text-slate-700",
  Contacted: "bg-blue-100 text-blue-700",
  "Follow-up": "bg-amber-100 text-amber-700",
  Meeting: "bg-purple-100 text-purple-700",
  "Proposal Sent": "bg-indigo-100 text-indigo-700",
  Successful: "bg-emerald-100 text-emerald-700",
  "Not Interested": "bg-rose-100 text-rose-700",
};

export const PRIORITY_STYLES = {
  High: "bg-emerald-100 text-emerald-700",
  Medium: "bg-amber-100 text-amber-700",
  Low: "bg-slate-100 text-slate-600",
};

export const EMAIL_TYPES = [
  { value: "first_outreach", label: "First Outreach" },
  { value: "follow_up", label: "Follow-up" },
  { value: "meeting_request", label: "Meeting Request" },
  { value: "thank_you", label: "Thank You" },
];
