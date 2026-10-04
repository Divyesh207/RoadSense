// Demo request form (landing page). The platform API has no demo-request endpoint, so the
// form is frontend-only: it validates the entry and prepares a summary the visitor can copy.

export interface DemoRequest {
  name: string;
  organization: string;
  email: string;
  phone: string;
  message: string;
}

export type DemoRequestErrors = Partial<Record<keyof DemoRequest, string>>;

export const EMPTY_DEMO_REQUEST: DemoRequest = { name: "", organization: "", email: "", phone: "", message: "" };

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const PHONE_PATTERN = /^\+?[0-9 ()-]{7,20}$/;

export function isValidEmail(value: string): boolean {
  return EMAIL_PATTERN.test(value.trim());
}

export function validateDemoRequest(form: DemoRequest): DemoRequestErrors {
  const errors: DemoRequestErrors = {};
  if (form.name.trim().length < 2) errors.name = "Enter your name.";
  if (form.organization.trim().length < 2) errors.organization = "Enter your organization.";
  if (!form.email.trim()) errors.email = "Enter your email address.";
  else if (!isValidEmail(form.email)) errors.email = "Enter a valid email address.";
  if (form.phone.trim() && !PHONE_PATTERN.test(form.phone.trim())) {
    errors.phone = "Enter a valid phone number, or leave it empty.";
  }
  if (form.message.trim().length < 10) errors.message = "Describe your use case in a sentence or two.";
  else if (form.message.length > 1000) errors.message = "Keep the message under 1000 characters.";
  return errors;
}

/** Plain-text summary the visitor can copy into their own email. */
export function demoRequestSummary(form: DemoRequest): string {
  const lines = [
    "Road Intelligence demo request",
    `Name: ${form.name.trim()}`,
    `Organization: ${form.organization.trim()}`,
    `Email: ${form.email.trim()}`,
  ];
  if (form.phone.trim()) lines.push(`Phone: ${form.phone.trim()}`);
  lines.push("", form.message.trim());
  return lines.join("\n");
}
