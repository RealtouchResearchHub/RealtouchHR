import React from 'react';
import { Link } from 'react-router-dom';

function Section({ id, title, children }) {
    return (
        <section id={id} className="mb-10">
            <h2 className="text-xl font-semibold text-foreground mb-3">{title}</h2>
            <div className="space-y-3 text-muted-foreground leading-relaxed">{children}</div>
        </section>
    );
}

export default function PrivacyPolicyPage() {
    const sections = [
        { id: 'intro', label: 'Introduction' },
        { id: 'controller', label: 'Data Controller' },
        { id: 'what-we-collect', label: 'Information We Collect' },
        { id: 'how-we-use', label: 'How We Use Your Data' },
        { id: 'legal-basis', label: 'Legal Basis for Processing' },
        { id: 'sharing', label: 'Data Sharing & Processors' },
        { id: 'international', label: 'International Transfers' },
        { id: 'retention', label: 'Data Retention' },
        { id: 'your-rights', label: 'Your Rights' },
        { id: 'security', label: 'Security' },
        { id: 'cookies', label: 'Cookies' },
        { id: 'children', label: "Children's Data" },
        { id: 'changes', label: 'Changes to This Policy' },
        { id: 'contact', label: 'Contact Us' },
    ];

    return (
        <div className="min-h-screen bg-background text-foreground">
            {/* Header */}
            <header className="border-b border-border sticky top-0 bg-background/95 backdrop-blur z-10">
                <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
                    <Link to="/">
                        <img src="/logo-white.png" alt="RealtouchHR" className="h-8 w-auto block dark:hidden" />
                        <img src="/logo-dark.png" alt="RealtouchHR" className="h-8 w-auto hidden dark:block" />
                    </Link>
                    <Link to="/" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                        ← Back to home
                    </Link>
                </div>
            </header>

            <div className="max-w-6xl mx-auto px-6 py-12 flex gap-12">
                {/* Sidebar navigation */}
                <aside className="hidden lg:block w-56 flex-shrink-0">
                    <div className="sticky top-24 space-y-1">
                        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">Contents</p>
                        {sections.map(s => (
                            <a
                                key={s.id}
                                href={`#${s.id}`}
                                className="block text-sm text-muted-foreground hover:text-foreground py-1 transition-colors"
                            >
                                {s.label}
                            </a>
                        ))}
                    </div>
                </aside>

                {/* Main content */}
                <main className="flex-1 min-w-0">
                    <div className="mb-8">
                        <h1 className="text-3xl font-bold text-foreground mb-2">Privacy Policy</h1>
                        <p className="text-muted-foreground">Last updated: 24 June 2026</p>
                    </div>

                    <Section id="intro" title="1. Introduction">
                        <p>
                            RealtouchHR Ltd ("we", "us", "our") operates the RealtouchHR platform, a cloud-based human resources and payroll management service designed for UK small and medium-sized businesses. This Privacy Policy explains how we collect, use, share, and protect your personal data when you use our website at <strong>realtouchhr.com</strong> and our associated services (collectively, the "Service").
                        </p>
                        <p>
                            We are committed to protecting your privacy and handling your data in an open and transparent manner in accordance with the UK General Data Protection Regulation (UK GDPR) and the Data Protection Act 2018.
                        </p>
                        <p>
                            Please read this policy carefully. By using our Service, you acknowledge that you have read and understood how we process your personal data.
                        </p>
                    </Section>

                    <Section id="controller" title="2. Data Controller">
                        <p>
                            RealtouchHR Ltd is the data controller for the personal data of account holders (administrators and owners) and is a data processor in relation to the employee personal data that your organisation inputs into the platform.
                        </p>
                        <p>
                            If you are an employee whose data has been entered into RealtouchHR by your employer, your employer is the data controller for your personal data and you should contact them directly with any enquiries.
                        </p>
                        <p>
                            You can contact our Data Protection Officer at: <strong>privacy@realtouchhr.com</strong>
                        </p>
                    </Section>

                    <Section id="what-we-collect" title="3. Information We Collect">
                        <p>We collect and process the following categories of personal data:</p>

                        <p className="font-medium text-foreground mt-4">Account and Registration Data</p>
                        <ul className="list-disc ml-5 space-y-1">
                            <li>Full name and email address</li>
                            <li>Password (stored as a one-way cryptographic hash)</li>
                            <li>Company name and registration number</li>
                            <li>Role and permissions within the platform</li>
                        </ul>

                        <p className="font-medium text-foreground mt-4">Employee Data (entered by your organisation)</p>
                        <ul className="list-disc ml-5 space-y-1">
                            <li>Full name, date of birth, National Insurance number</li>
                            <li>Contact details (home address, personal email, phone number)</li>
                            <li>Right to work status and visa/immigration details (where applicable)</li>
                            <li>Employment details: job title, department, start date, salary, contract type</li>
                            <li>Bank account details for payroll processing</li>
                            <li>Tax codes and payroll history</li>
                            <li>Leave entitlements and absence records</li>
                            <li>Performance and training records</li>
                            <li>Documents and certifications</li>
                            <li>Profile photographs (if uploaded)</li>
                        </ul>

                        <p className="font-medium text-foreground mt-4">Usage and Technical Data</p>
                        <ul className="list-disc ml-5 space-y-1">
                            <li>Log data: IP address, browser type, pages visited, timestamps</li>
                            <li>Device information</li>
                            <li>Session tokens and authentication data</li>
                            <li>Feature usage analytics (aggregated and anonymised where possible)</li>
                        </ul>

                        <p className="font-medium text-foreground mt-4">Third-Party Sign-In</p>
                        <p>
                            If you sign up or log in using Google OAuth, we receive your name and email address from Google. We do not receive your Google password.
                        </p>
                    </Section>

                    <Section id="how-we-use" title="4. How We Use Your Data">
                        <p>We use the personal data we collect for the following purposes:</p>
                        <ul className="list-disc ml-5 space-y-2 mt-2">
                            <li><strong>Providing the Service:</strong> To create and manage your account, process payroll, manage employee records, generate compliance reports, and deliver all platform features.</li>
                            <li><strong>Communications:</strong> To send you service-related emails such as account creation confirmations, password resets, and important platform notifications. We will not send marketing emails without your explicit consent.</li>
                            <li><strong>Customer Support:</strong> To respond to your queries, troubleshoot issues, and improve the Service.</li>
                            <li><strong>Security and Fraud Prevention:</strong> To detect, prevent, and respond to fraud, abuse, and security incidents.</li>
                            <li><strong>Legal Compliance:</strong> To comply with our legal obligations under UK employment law, tax law, and data protection law.</li>
                            <li><strong>Service Improvement:</strong> To analyse usage patterns and improve our platform (using anonymised and aggregated data where possible).</li>
                            <li><strong>Billing:</strong> To process subscription payments and manage your account.</li>
                        </ul>
                    </Section>

                    <Section id="legal-basis" title="5. Legal Basis for Processing">
                        <p>Under UK GDPR, we process your personal data on the following legal bases:</p>
                        <ul className="list-disc ml-5 space-y-2 mt-2">
                            <li><strong>Performance of a Contract (Article 6(1)(b)):</strong> Processing necessary to deliver the RealtouchHR Service to you under our Terms of Service.</li>
                            <li><strong>Legal Obligation (Article 6(1)(c)):</strong> Processing required to comply with UK law, including payroll tax obligations under HMRC rules.</li>
                            <li><strong>Legitimate Interests (Article 6(1)(f)):</strong> Processing for security, fraud prevention, service improvement, and audit logging where our interests are not overridden by your rights.</li>
                            <li><strong>Consent (Article 6(1)(a)):</strong> Where we rely on your consent (for example, for optional marketing communications), you may withdraw consent at any time.</li>
                        </ul>
                        <p className="mt-3">
                            For special category data (such as right-to-work documents containing immigration status), we rely on Article 9(2)(b) UK GDPR (processing necessary for employment law obligations) and Article 9(2)(g) (substantial public interest).
                        </p>
                    </Section>

                    <Section id="sharing" title="6. Data Sharing and Third-Party Processors">
                        <p>
                            We do not sell your personal data. We share data only with trusted third-party service providers ("processors") who assist us in operating the Service, under strict data processing agreements:
                        </p>
                        <div className="overflow-x-auto mt-3">
                            <table className="w-full text-sm border border-border rounded">
                                <thead>
                                    <tr className="bg-muted">
                                        <th className="px-4 py-2 text-left font-medium text-foreground">Processor</th>
                                        <th className="px-4 py-2 text-left font-medium text-foreground">Purpose</th>
                                        <th className="px-4 py-2 text-left font-medium text-foreground">Location</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-border">
                                    <tr><td className="px-4 py-2">Supabase Inc.</td><td className="px-4 py-2">Database and cloud storage</td><td className="px-4 py-2">EU / USA</td></tr>
                                    <tr><td className="px-4 py-2">Resend Inc.</td><td className="px-4 py-2">Transactional email delivery</td><td className="px-4 py-2">USA</td></tr>
                                    <tr><td className="px-4 py-2">Stripe Inc.</td><td className="px-4 py-2">Payment processing</td><td className="px-4 py-2">USA</td></tr>
                                    <tr><td className="px-4 py-2">Google LLC</td><td className="px-4 py-2">Optional OAuth sign-in</td><td className="px-4 py-2">USA</td></tr>
                                    <tr><td className="px-4 py-2">Companies House (HMRC)</td><td className="px-4 py-2">Company verification</td><td className="px-4 py-2">UK</td></tr>
                                </tbody>
                            </table>
                        </div>
                        <p className="mt-3">
                            We may also disclose data to law enforcement or regulatory authorities where required by law, or to protect the rights and safety of our users.
                        </p>
                    </Section>

                    <Section id="international" title="7. International Data Transfers">
                        <p>
                            Some of our third-party processors are based outside the UK or the European Economic Area (EEA). Where we transfer personal data internationally, we ensure appropriate safeguards are in place, including:
                        </p>
                        <ul className="list-disc ml-5 space-y-1 mt-2">
                            <li>UK International Data Transfer Agreements (IDTAs) or equivalent standard contractual clauses</li>
                            <li>Transfers to countries with an adequacy decision from the UK Secretary of State</li>
                        </ul>
                        <p className="mt-3">
                            You can request details of the specific safeguards in place by contacting us at <strong>privacy@realtouchhr.com</strong>.
                        </p>
                    </Section>

                    <Section id="retention" title="8. Data Retention">
                        <p>We retain your personal data for as long as necessary to fulfil the purposes for which it was collected, including legal and regulatory requirements:</p>
                        <ul className="list-disc ml-5 space-y-2 mt-2">
                            <li><strong>Account data:</strong> For the duration of your subscription plus 7 years (to comply with HMRC record-keeping requirements).</li>
                            <li><strong>Payroll records:</strong> 7 years from the end of the relevant tax year (HMRC requirement).</li>
                            <li><strong>Right to work documents:</strong> 2 years after the end of employment.</li>
                            <li><strong>Audit logs:</strong> 7 years.</li>
                            <li><strong>Deleted account data:</strong> Purged within 90 days of account closure, except where retention is required by law.</li>
                        </ul>
                        <p className="mt-3">
                            When data is no longer required, it is securely deleted or anonymised.
                        </p>
                    </Section>

                    <Section id="your-rights" title="9. Your Rights Under UK GDPR">
                        <p>You have the following rights regarding your personal data:</p>
                        <ul className="list-disc ml-5 space-y-2 mt-2">
                            <li><strong>Right of Access (Article 15):</strong> You can request a copy of the personal data we hold about you (a Subject Access Request).</li>
                            <li><strong>Right to Rectification (Article 16):</strong> You can ask us to correct inaccurate or incomplete data.</li>
                            <li><strong>Right to Erasure (Article 17):</strong> You can ask us to delete your data in certain circumstances ("the right to be forgotten").</li>
                            <li><strong>Right to Restrict Processing (Article 18):</strong> You can ask us to suspend processing of your data in certain circumstances.</li>
                            <li><strong>Right to Data Portability (Article 20):</strong> You can request your data in a structured, machine-readable format.</li>
                            <li><strong>Right to Object (Article 21):</strong> You can object to processing based on legitimate interests.</li>
                            <li><strong>Rights in Relation to Automated Decision-Making (Article 22):</strong> You have the right not to be subject to solely automated decisions that significantly affect you.</li>
                        </ul>
                        <p className="mt-3">
                            To exercise any of these rights, contact us at <strong>privacy@realtouchhr.com</strong>. We will respond within one calendar month. If you are unsatisfied with our response, you have the right to lodge a complaint with the Information Commissioner's Office (ICO) at <strong>ico.org.uk</strong> or by calling 0303 123 1113.
                        </p>
                    </Section>

                    <Section id="security" title="10. Security">
                        <p>
                            We implement appropriate technical and organisational measures to protect your personal data against unauthorised access, loss, or disclosure, including:
                        </p>
                        <ul className="list-disc ml-5 space-y-1 mt-2">
                            <li>Encryption of data in transit (TLS 1.2+) and at rest</li>
                            <li>Bcrypt hashing for passwords</li>
                            <li>JWT-based session tokens with secure HttpOnly cookies</li>
                            <li>Role-based access control</li>
                            <li>Audit logging of all data access and changes</li>
                            <li>Two-factor authentication (2FA) option for accounts</li>
                            <li>Regular security assessments</li>
                        </ul>
                        <p className="mt-3">
                            Despite these measures, no method of transmission over the internet is 100% secure. If you believe your account has been compromised, please contact us immediately at <strong>security@realtouchhr.com</strong>.
                        </p>
                    </Section>

                    <Section id="cookies" title="11. Cookies">
                        <p>
                            We use cookies and similar technologies to operate the Service and improve your experience:
                        </p>
                        <ul className="list-disc ml-5 space-y-2 mt-2">
                            <li><strong>Strictly Necessary Cookies:</strong> Session tokens required for authentication. These cannot be disabled without affecting your ability to use the Service.</li>
                            <li><strong>Preference Cookies:</strong> Store your theme and display preferences (light/dark mode).</li>
                            <li><strong>Analytics Cookies:</strong> Used to understand how the Service is used (where consent has been obtained).</li>
                        </ul>
                        <p className="mt-3">
                            You can control cookies through your browser settings. Disabling strictly necessary cookies will prevent you from logging in.
                        </p>
                    </Section>

                    <Section id="children" title="12. Children's Data">
                        <p>
                            The RealtouchHR Service is intended for use by businesses and is not directed at individuals under the age of 18. We do not knowingly collect personal data from children. If you believe we have inadvertently collected such data, please contact us at <strong>privacy@realtouchhr.com</strong> and we will delete it promptly.
                        </p>
                    </Section>

                    <Section id="changes" title="13. Changes to This Policy">
                        <p>
                            We may update this Privacy Policy from time to time to reflect changes in our practices, technology, or legal requirements. When we make material changes, we will notify you by email and by posting a notice on the Service at least 30 days before the changes take effect. Your continued use of the Service after that date constitutes acceptance of the updated policy.
                        </p>
                        <p>
                            The date at the top of this document indicates when this policy was last updated.
                        </p>
                    </Section>

                    <Section id="contact" title="14. Contact Us">
                        <p>If you have any questions, concerns, or requests relating to this Privacy Policy or our data practices, please contact us:</p>
                        <div className="mt-3 p-4 bg-muted rounded-lg space-y-1">
                            <p><strong>RealtouchHR Ltd</strong></p>
                            <p>Data Protection Officer</p>
                            <p>Email: <a href="mailto:privacy@realtouchhr.com" className="text-indigo-600 hover:underline">privacy@realtouchhr.com</a></p>
                            <p>Website: <Link to="/" className="text-indigo-600 hover:underline">realtouchhr.com</Link></p>
                        </div>
                        <p className="mt-3">
                            For complaints, you may also contact the UK Information Commissioner's Office (ICO):
                        </p>
                        <div className="mt-2 p-4 bg-muted rounded-lg space-y-1">
                            <p><strong>Information Commissioner's Office</strong></p>
                            <p>Wycliffe House, Water Lane, Wilmslow, Cheshire, SK9 5AF</p>
                            <p>Tel: 0303 123 1113</p>
                            <p><a href="https://ico.org.uk" target="_blank" rel="noopener noreferrer" className="text-indigo-600 hover:underline">ico.org.uk</a></p>
                        </div>
                    </Section>
                </main>
            </div>

            <footer className="border-t border-border py-8 mt-12">
                <div className="max-w-6xl mx-auto px-6 flex flex-wrap items-center justify-between gap-4 text-sm text-muted-foreground">
                    <p>© 2026 RealtouchHR Ltd. All rights reserved.</p>
                    <div className="flex gap-4">
                        <Link to="/" className="hover:text-foreground transition-colors">Home</Link>
                        <Link to="/privacy" className="hover:text-foreground transition-colors">Privacy Policy</Link>
                    </div>
                </div>
            </footer>
        </div>
    );
}
