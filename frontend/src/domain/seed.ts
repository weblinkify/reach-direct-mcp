export type Channel = 'email' | 'whatsapp';

export interface Contact {
  id: string;
  name: string;
  company: string;
  email: string;
  phone: string;
  city: string;
}

/** Fictional contacts for the demo. */
export const CONTACTS: Contact[] = [
  { id: 'c1', name: 'Marie Laurent', company: 'Laurent Remorques', email: 'marie.laurent@laurent-remorques.example', phone: '+33 6 12 34 56 78', city: 'Lyon' },
  { id: 'c2', name: 'Mehmet Yılmaz', company: 'Ege Ambalaj', email: 'mehmet.yilmaz@ege-ambalaj.example', phone: '+90 532 123 45 67', city: 'İzmir' },
  { id: 'c3', name: 'Anna Koivisto', company: 'Koivu Paahtimo', email: 'anna.koivisto@koivu-paahtimo.example', phone: '+358 40 123 4567', city: 'Tampere' },
  { id: 'c4', name: 'Klaus Fischer', company: 'Agro Implements', email: 'k.fischer@agro-implements.example', phone: '+49 151 2345 6789', city: 'Hannover' },
  { id: 'c5', name: 'Sarah Hughes', company: 'Pennine Office Supplies', email: 'sarah.hughes@pennine-office.example', phone: '', city: 'Leeds' },
];

export const TEMPLATES: { id: string; label: string; subject: string; body: string }[] = [
  {
    id: 'intro', label: 'Intro',
    subject: 'Quick question for {{company}}',
    body: `Hi {{first_name|there}},

I came across {{company}} while looking at distributors in {{city|your region}}. We make {{product|heavy-duty trailer parts}} and already supply two dealers nearby.

Would a 15-minute call next week be useful? If not, just reply "no thanks" and I won't follow up.

Best regards,
{{sender_name}}`,
  },
  {
    id: 'followup', label: 'Follow-up',
    subject: 'Following up, {{first_name}}',
    body: `Hi {{first_name}},

Just following up on my email last week about {{product|our parts range}}. Happy to send a price list for {{company}} if that helps.

{{sender_name}}`,
  },
  {
    id: 'whatsapp', label: 'WhatsApp nudge',
    subject: '',
    body: `Hi {{first_name}}, this is {{sender_name}}. I sent you an email about {{product|our parts range}} for {{company}}. Is WhatsApp easier for a quick chat?`,
  },
];
