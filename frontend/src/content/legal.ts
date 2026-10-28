/**
 * Legal pages (ES/EN). Fill the OWNER block before publishing. These texts follow the usual structure
 * for a Spanish-based personal website (LSSI-CE art. 10, GDPR / LOPDGDD, AEPD cookies guide); they are
 * not a substitute for a lawyer's review.
 */
export const OWNER = {
  name: 'Iñigo González García',
  taxId: '[NIF]',
  address: '[dirección postal — rellenar antes de publicar]',
  email: '[correo de contacto]',
  site: 'https://inigogonzalezgarcia.github.io',
  contactForm: 'https://inigogonzalezgarcia.github.io/about.html#contacto',
};

export type LegalPage = { slug: string; title: { es: string; en: string }; sections: { heading: { es: string; en: string }; body: { es: string[]; en: string[] } }[] };

const o = OWNER;

export const LEGAL: LegalPage[] = [
  {
    slug: 'aviso',
    title: { es: 'Aviso legal', en: 'Legal notice' },
    sections: [
      {
        heading: { es: 'Titular del sitio', en: 'Site owner' },
        body: {
          es: [`Titular: ${o.name}. NIF: ${o.taxId}. Domicilio: ${o.address}. Contacto: ${o.email} o el formulario de ${o.contactForm}.`, 'Este sitio ("FX Research Lab") es un proyecto personal de carácter educativo. La información anterior se facilita en cumplimiento del artículo 10 de la Ley 34/2002, de servicios de la sociedad de la información y de comercio electrónico (LSSI-CE).'],
          en: [`Owner: ${o.name}. Tax ID: ${o.taxId}. Address: ${o.address}. Contact: ${o.email} or the form at ${o.contactForm}.`, 'This site ("FX Research Lab") is a personal educational project. The information above is provided under article 10 of Spanish Law 34/2002 on information-society services (LSSI-CE).'],
        },
      },
      {
        heading: { es: 'Naturaleza educativa. Sin asesoramiento', en: 'Educational nature. No advice' },
        body: {
          es: ['FX Research Lab es un simulador educativo de investigación de estrategias. Todo su contenido (lecciones, resultados, gráficos, informes y código) tiene finalidad exclusivamente formativa y divulgativa.', 'Nada en este sitio constituye asesoramiento de inversión, recomendación personalizada, análisis financiero ni oferta o invitación a operar con ningún instrumento. El titular no es una empresa de servicios de inversión ni un asesor financiero autorizado o registrado ante la CNMV ni ante ningún otro supervisor.', 'Los resultados mostrados son simulaciones sobre datos históricos obtenidas con las reglas y los supuestos de ejecución registrados en cada caso. No son evidencia de una ventaja rentable y el rendimiento pasado no garantiza resultados futuros. La operativa en divisas con apalancamiento conlleva un alto riesgo de pérdida.', 'El sitio no se conecta a ningún bróker, no ejecuta órdenes y no emite señales ni alertas.'],
          en: ['FX Research Lab is an educational strategy-research simulator. All its content (lessons, results, charts, reports and code) is for learning and informational purposes only.', 'Nothing on this site constitutes investment advice, a personal recommendation, financial analysis, or an offer or solicitation to trade any instrument. The owner is not an investment firm nor a financial adviser authorised or registered with the CNMV or any other supervisor.', 'The results shown are simulations on historical data produced with the rules and execution assumptions recorded in each case. They are not evidence of a profitable edge and past performance does not guarantee future results. Trading leveraged foreign exchange involves a high risk of loss.', 'The site does not connect to any broker, does not execute orders and does not issue signals or alerts.'],
        },
      },
      {
        heading: { es: 'Propiedad intelectual', en: 'Intellectual property' },
        body: {
          es: ['El código del laboratorio se publica bajo licencia MIT en el repositorio enlazado en el pie de página. Los textos de las lecciones, el diseño y los materiales del sitio son propiedad del titular; se permite su cita con mención de la fuente y enlace. No se permite su reproducción íntegra ni su uso comercial sin autorización.', 'Los datos de mercado proceden de fuentes de terceros (indicadas en cada resultado) y están sujetos a sus propias condiciones.'],
          en: ['The lab code is published under the MIT License in the repository linked in the footer. Lesson texts, design and site materials belong to the owner; quoting with attribution and a link is allowed. Full reproduction or commercial use without permission is not.', 'Market data comes from third-party sources (named in each result) and is subject to their own terms.'],
        },
      },
      {
        heading: { es: 'Responsabilidad', en: 'Liability' },
        body: {
          es: ['El titular no responde de las decisiones que el usuario tome a partir del contenido del sitio ni de los daños derivados de su uso. El contenido se ofrece "tal cual", sin garantía de exactitud, integridad o disponibilidad. Los enlaces a sitios de terceros se facilitan a título informativo.'],
          en: ['The owner is not liable for decisions users make based on the site content nor for damages arising from its use. Content is provided "as is", without warranty of accuracy, completeness or availability. Links to third-party sites are provided for information only.'],
        },
      },
      {
        heading: { es: 'Legislación y jurisdicción', en: 'Governing law and jurisdiction' },
        body: {
          es: ['Este aviso se rige por la legislación española. Para cualquier controversia, y salvo que la normativa de consumidores establezca otro fuero, serán competentes los juzgados y tribunales del domicilio del titular.'],
          en: ['This notice is governed by Spanish law. Any dispute, unless consumer law provides another venue, falls under the courts of the owner\'s domicile.'],
        },
      },
    ],
  },
  {
    slug: 'privacidad',
    title: { es: 'Política de privacidad', en: 'Privacy policy' },
    sections: [
      {
        heading: { es: 'Responsable', en: 'Controller' },
        body: { es: [`${o.name}, NIF ${o.taxId}, ${o.address}. Contacto: ${o.email}.`], en: [`${o.name}, tax ID ${o.taxId}, ${o.address}. Contact: ${o.email}.`] },
      },
      {
        heading: { es: 'Qué datos se tratan y para qué', en: 'What data is processed and why' },
        body: {
          es: ['Lista de correo. Si te apuntas, se guarda tu dirección de correo, el idioma elegido, la fecha y hora del consentimiento, la página desde la que te apuntaste y un resumen (hash) de tu dirección IP como prueba del consentimiento. Finalidad: enviarte avisos sobre novedades de FX Research Lab (lecciones, módulos, informes). Base jurídica: tu consentimiento (art. 6.1.a RGPD), que puedes retirar en cualquier momento.', 'Formulario de contacto. Se gestiona en el sitio web del titular, con su propia política.', 'Progreso en las lecciones. Se guarda únicamente en tu navegador (localStorage); no se envía a ningún servidor ni se asocia a tu identidad.', 'Registros técnicos. Cloudflare, como proveedor de alojamiento, procesa direcciones IP y datos de conexión para prestar el servicio y protegerlo (registros de seguridad, Turnstile anti-bots). Base jurídica: interés legítimo en la seguridad del servicio (art. 6.1.f RGPD).', 'No se usan cookies de seguimiento ni herramientas de analítica de terceros.'],
          en: ['Mailing list. If you sign up, your email address, chosen language, consent timestamp, the page you signed up from and a hash of your IP address (as evidence of consent) are stored. Purpose: to send you notices about FX Research Lab news (lessons, modules, reports). Legal basis: your consent (art. 6(1)(a) GDPR), which you can withdraw at any time.', 'Contact form. Handled on the owner\'s website, under its own policy.', 'Lesson progress. Stored only in your browser (localStorage); never sent to a server nor linked to your identity.', 'Technical logs. Cloudflare, as hosting provider, processes IP addresses and connection data to deliver and protect the service (security logs, Turnstile anti-bot). Legal basis: legitimate interest in service security (art. 6(1)(f) GDPR).', 'No tracking cookies or third-party analytics are used.'],
        },
      },
      {
        heading: { es: 'Destinatarios y transferencias', en: 'Recipients and transfers' },
        body: {
          es: ['Los datos se alojan en la infraestructura de Cloudflare, Inc. (encargado del tratamiento), que puede tratar datos fuera del Espacio Económico Europeo bajo las Cláusulas Contractuales Tipo de la Comisión Europea y el Marco de Privacidad de Datos UE-EE. UU. No se ceden datos a otros terceros ni se venden.'],
          en: ['Data is hosted on the infrastructure of Cloudflare, Inc. (processor), which may process data outside the European Economic Area under the European Commission\'s Standard Contractual Clauses and the EU-US Data Privacy Framework. Data is not shared with other third parties nor sold.'],
        },
      },
      {
        heading: { es: 'Conservación', en: 'Retention' },
        body: {
          es: ['La dirección de la lista de correo se conserva hasta que te des de baja o solicites su supresión, y hasta un máximo de 24 meses sin actividad. La prueba del consentimiento se conserva mientras dure el tratamiento y el plazo de prescripción de las posibles responsabilidades.'],
          en: ['Mailing-list addresses are kept until you unsubscribe or request deletion, and at most 24 months without activity. Evidence of consent is kept for the duration of the processing and the limitation period for potential liability.'],
        },
      },
      {
        heading: { es: 'Tus derechos', en: 'Your rights' },
        body: {
          es: [`Puedes ejercer los derechos de acceso, rectificación, supresión, oposición, limitación y portabilidad escribiendo a ${o.email}. Cada correo de la lista incluye un enlace de baja. Si consideras que el tratamiento no es conforme, puedes reclamar ante la Agencia Española de Protección de Datos (www.aepd.es).`],
          en: [`You may exercise your rights of access, rectification, erasure, objection, restriction and portability by writing to ${o.email}. Every list email includes an unsubscribe link. If you believe the processing is unlawful you may lodge a complaint with the Spanish Data Protection Agency (www.aepd.es).`],
        },
      },
    ],
  },
  {
    slug: 'cookies',
    title: { es: 'Política de cookies', en: 'Cookie policy' },
    sections: [
      {
        heading: { es: 'Qué usa este sitio', en: 'What this site uses' },
        body: {
          es: ['Este sitio no utiliza cookies de analítica, publicidad ni seguimiento. Por eso no muestra un banner de cookies.', 'Almacenamiento técnico en tu navegador (localStorage): idioma elegido (fxlab.lang) y progreso de las lecciones (fxlab.progress). No identifican a la persona, no se envían a ningún servidor y puedes borrarlos desde la configuración del navegador.', 'Cloudflare puede establecer cookies estrictamente técnicas para la seguridad del servicio (por ejemplo, las asociadas a Turnstile en el formulario de la lista de correo). Están exentas de consentimiento según la guía de la AEPD por ser necesarias para la prestación del servicio.'],
          en: ['This site uses no analytics, advertising or tracking cookies. That is why it shows no cookie banner.', 'Technical storage in your browser (localStorage): chosen language (fxlab.lang) and lesson progress (fxlab.progress). They do not identify you, are never sent to a server and can be cleared from your browser settings.', 'Cloudflare may set strictly technical cookies for service security (for instance those tied to Turnstile on the mailing-list form). They are exempt from consent under the AEPD guidance as necessary to provide the service.'],
        },
      },
    ],
  },
  {
    slug: 'condiciones',
    title: { es: 'Condiciones de uso', en: 'Terms of use' },
    sections: [
      {
        heading: { es: 'Aceptación', en: 'Acceptance' },
        body: { es: ['El uso de este sitio implica la aceptación de estas condiciones, del aviso legal y de la política de privacidad.'], en: ['Using this site implies acceptance of these terms, the legal notice and the privacy policy.'] },
      },
      {
        heading: { es: 'Uso permitido', en: 'Permitted use' },
        body: {
          es: ['El sitio se ofrece para aprender a investigar estrategias de trading con método. Puedes consultar los resultados, seguir las lecciones y usar el código del repositorio conforme a su licencia MIT. No está permitido presentar el contenido como recomendación de inversión propia o ajena, revenderlo, automatizar su extracción masiva ni interferir con el servicio.'],
          en: ['The site is offered to learn how to research trading strategies with method. You may consult the results, follow the lessons and use the repository code under its MIT License. You may not present the content as investment advice (your own or anyone else\'s), resell it, scrape it at scale or interfere with the service.'],
        },
      },
      {
        heading: { es: 'Contenido educativo y riesgo', en: 'Educational content and risk' },
        body: {
          es: ['Todo el contenido es simulado y educativo. Cualquier decisión de inversión es responsabilidad exclusiva de quien la toma. El titular recomienda no operar con dinero real sobre la base de nada de lo publicado aquí y consultar a un asesor regulado antes de invertir.'],
          en: ['All content is simulated and educational. Any investment decision is the sole responsibility of the person making it. The owner recommends not trading real money on the basis of anything published here and consulting a regulated adviser before investing.'],
        },
      },
      {
        heading: { es: 'Productos de pago (cuando existan)', en: 'Paid products (when available)' },
        body: {
          es: ['Si en el futuro se ofrecen cursos o materiales de pago, se venderán a través de un proveedor de pagos que actúa como vendedor registrado (por ejemplo, Lemon Squeezy), con sus propias condiciones de compra, facturación e IVA. Al tratarse de contenido digital de entrega inmediata, el comprador será informado de que, al solicitar el acceso, pierde el derecho de desistimiento conforme al artículo 103.m) del Real Decreto Legislativo 1/2007, y deberá consentirlo expresamente antes de la compra.'],
          en: ['If paid courses or materials are offered in the future, they will be sold through a payment provider acting as merchant of record (for example Lemon Squeezy), under its own purchase, invoicing and VAT terms. As digital content delivered immediately, buyers will be informed that by requesting access they waive the right of withdrawal under article 103(m) of Spanish Royal Legislative Decree 1/2007, and must expressly consent to this before purchase.'],
        },
      },
      {
        heading: { es: 'Modificaciones', en: 'Changes' },
        body: { es: ['El titular puede modificar estas condiciones y el contenido del sitio en cualquier momento. La versión vigente es la publicada en esta página.'], en: ['The owner may modify these terms and the site content at any time. The current version is the one published on this page.'] },
      },
    ],
  },
];
