const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, AlignmentType, VerticalAlign,
  Footer, PageNumber, TabStopType, TabStopPosition, PageBreak, ImageRun,
} = require("docx");
const path = require("path");

// ---- Color system (mandatory, exact) ----
const NAVY = "17243A";
const SLATE = "526174";
const LIGHTGRAY = "F3F5F7";
const BORDERGRAY = "D9DEE5";
const GOLD = "B59A5A";
const BLACK = "111111";
const WHITE = "FFFFFF";

// ---- Font: Aptos only ----
const FONT = "Aptos";

// ---- Page geometry (exact) ----
const PAGE_W = 12240, PAGE_H = 15840; // 8.5 x 11, twips
const MARGIN_TOP = 864;    // 0.60"
const MARGIN_BOTTOM = 864; // 0.60"
const MARGIN_LEFT = 1008;  // 0.70"
const MARGIN_RIGHT = 1008; // 0.70"
const HEADER_DIST = 432;   // 0.30"
const FOOTER_DIST = 432;   // 0.30"
const CONTENT_W = PAGE_W - MARGIN_LEFT - MARGIN_RIGHT; // 10224

// "Why Sellers" grid cell padding (twips; 1px @96dpi = 15 twips).
// top 100tw ~= 6.7px, bottom/right 260tw ~= 17.3px. Widened 2026-08-18 so 5
// items in a 2x3 grid (one empty cell) read as intentional breathing room,
// not a document straining to look full — see SKILL.md content rules.
// Revise spacing requests by editing these two numbers only.
const WHY_CELL_MARGINS = { top: 100, bottom: 260, left: 0, right: 260 };

const pt = (p) => Math.round(p * 20); // pt -> twentieths-of-a-point (character spacing / half-point sizes handled separately)
const half = (p) => Math.round(p * 2); // pt -> half-points (font size)

function noBorders() {
  return {
    top: { style: BorderStyle.NONE, size: 0, color: WHITE },
    bottom: { style: BorderStyle.NONE, size: 0, color: WHITE },
    left: { style: BorderStyle.NONE, size: 0, color: WHITE },
    right: { style: BorderStyle.NONE, size: 0, color: WHITE },
    insideHorizontal: { style: BorderStyle.NONE, size: 0, color: WHITE },
    insideVertical: { style: BorderStyle.NONE, size: 0, color: WHITE },
  };
}

function rowSeparatorBorders(size = 3) {
  // One continuous light-gray sheet — only a hairline between rows, no vertical
  // divider, no gutter. Columns separate purely through internal padding.
  return {
    top: { style: BorderStyle.NONE, size: 0, color: WHITE },
    bottom: { style: BorderStyle.NONE, size: 0, color: WHITE },
    left: { style: BorderStyle.NONE, size: 0, color: WHITE },
    right: { style: BorderStyle.NONE, size: 0, color: WHITE },
    insideHorizontal: { style: BorderStyle.SINGLE, size, color: BORDERGRAY },
    insideVertical: { style: BorderStyle.NONE, size: 0, color: WHITE },
  };
}

function hairlineBorder(color = BORDERGRAY, size = 4) {
  return {
    top: { style: BorderStyle.SINGLE, size, color },
    bottom: { style: BorderStyle.SINGLE, size, color },
    left: { style: BorderStyle.SINGLE, size, color },
    right: { style: BorderStyle.SINGLE, size, color },
  };
}

// ---------- Word styles (defined once, referenced throughout) ----------

const paragraphStyles = [
  {
    id: "OxfordCompanyName", name: "Oxford Company Name", basedOn: "Normal", next: "Normal", quickFormat: true,
    run: { font: FONT, size: half(17), bold: true, color: NAVY, characterSpacing: pt(0.5) },
    paragraph: { spacing: { after: pt(2) } },
  },
  {
    id: "ProposalTitle", name: "Proposal Title", basedOn: "Normal", next: "Normal", quickFormat: true,
    run: { font: FONT, size: half(13.5), bold: true, color: NAVY, characterSpacing: pt(0.3) },
    paragraph: { spacing: { before: 0, after: pt(12) } },
  },
  {
    id: "PropertyAddress", name: "Property Address", basedOn: "Normal", next: "Normal", quickFormat: true,
    run: { font: FONT, size: half(15), bold: true, color: BLACK },
    paragraph: { spacing: { before: 0, after: pt(3) } },
  },
  {
    id: "SectionHeading", name: "Section Heading", basedOn: "Normal", next: "Normal", quickFormat: true,
    run: { font: FONT, size: half(10.5), bold: true, color: NAVY, characterSpacing: pt(0.4) },
    paragraph: { spacing: { before: pt(12), after: pt(6) } },
  },
  {
    id: "TermLabel", name: "Term Label", basedOn: "Normal", next: "Normal", quickFormat: true,
    run: { font: FONT, size: half(9), bold: true, color: SLATE, characterSpacing: pt(0.3) },
    paragraph: { spacing: { after: pt(2) } },
  },
  {
    id: "TermValue", name: "Term Value", basedOn: "Normal", next: "Normal", quickFormat: true,
    run: { font: FONT, size: half(10), bold: true, color: BLACK },
    paragraph: { spacing: { after: 0 } },
  },
  {
    id: "PrimaryTermValue", name: "Primary Term Value", basedOn: "Normal", next: "Normal", quickFormat: true,
    run: { font: FONT, size: half(17), bold: true, color: NAVY },
    paragraph: { spacing: { after: 0 } },
  },
  {
    id: "Body", name: "Body", basedOn: "Normal", next: "Normal", quickFormat: true,
    run: { font: FONT, size: half(9), bold: false, color: BLACK },
    paragraph: { spacing: { after: pt(5), line: 264, lineRule: "auto" } },
  },
  {
    id: "SmallBody", name: "Small Body", basedOn: "Normal", next: "Normal", quickFormat: true,
    run: { font: FONT, size: half(8.5), bold: false, color: BLACK },
    paragraph: { spacing: { after: pt(2), line: 260, lineRule: "auto" } },
  },
  {
    id: "Caption", name: "Caption", basedOn: "Normal", next: "Normal", quickFormat: true,
    run: { font: FONT, size: half(7.5), bold: false, color: SLATE },
    paragraph: { spacing: { after: pt(2) } },
  },
  {
    id: "Footer", name: "Footer", basedOn: "Normal", next: "Normal", quickFormat: true,
    run: { font: FONT, size: half(7.5), bold: false, color: SLATE },
    paragraph: { spacing: { after: 0 } },
  },
];

// ---------- PAGE 1 ----------

const companyName = new Paragraph({
  style: "OxfordCompanyName",
  children: [new TextRun({ text: "OXFORD REALTY ADVISORS" })],
});

const proposalTitle = new Paragraph({
  style: "ProposalTitle",
  children: [new TextRun({ text: "ACQUISITION PROPOSAL" })],
});

// Property / Date — a single stacked address block (street, city/state/zip,
// date beneath), left-aligned, no floating right-hand "DATE" label.
const propertyAddressLine1 = new Paragraph({
  style: "PropertyAddress",
  spacing: { before: 0, after: pt(1) },
  children: [new TextRun({ text: "[Property Address]" })],
});
const propertyAddressLine2 = new Paragraph({
  style: "PropertyAddress",
  spacing: { before: 0, after: pt(4) },
  children: [new TextRun({ text: "[City, State ZIP]" })],
});
const propertyDateLine = new Paragraph({
  spacing: { before: 0, after: 0 },
  children: [new TextRun({ text: "[Date]", font: FONT, size: half(10), bold: false, color: SLATE })],
});

const propertyRow = [propertyAddressLine1, propertyAddressLine2, propertyDateLine];

function sectionHeading(text, before) {
  return new Paragraph({
    style: "SectionHeading",
    spacing: before ? { before: pt(before), after: pt(6) } : undefined,
    children: [new TextRun({ text })],
  });
}

const proposedTermsHeading = sectionHeading("PROPOSED TERMS", 14);

// ---- 3 x 2 Proposed Terms grid ----
function gridCell(label, value, opts = {}) {
  const isPrimary = !!opts.primary;
  const isLeft = !!opts.left;
  const valueRun = opts.valueColor
    ? new TextRun({ text: value, color: opts.valueColor })
    : new TextRun({ text: value });
  return new TableCell({
    width: { size: Math.round(CONTENT_W * 0.5), type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, color: "auto", fill: LIGHTGRAY },
    margins: isPrimary
      ? { top: 240, bottom: 240, left: 280, right: 260 }
      : { top: 190, bottom: 190, left: isLeft ? 280 : 260, right: 260 },
    verticalAlign: VerticalAlign.CENTER,
    borders: isPrimary
      ? { left: { style: BorderStyle.SINGLE, size: 12, color: GOLD } }
      : undefined,
    children: [
      new Paragraph({ style: "TermLabel", children: [new TextRun({ text: label })] }),
      new Paragraph({ style: isPrimary ? "PrimaryTermValue" : "TermValue", children: [valueRun] }),
    ],
  });
}

const termsGrid = new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: [Math.round(CONTENT_W * 0.5), Math.round(CONTENT_W * 0.5)],
  borders: rowSeparatorBorders(3),
  rows: [
    new TableRow({
      children: [
        gridCell("PURCHASE PRICE", "$[______________]", { primary: true, left: true }),
        gridCell("DEPOSIT", "$[__________], refundable during Study Period"),
      ],
    }),
    new TableRow({
      children: [
        gridCell("STUDY PERIOD", "[__] days", { left: true }),
        gridCell("CLOSING", "[__] days following Study Period"),
      ],
    }),
    new TableRow({
      children: [
        gridCell("FINANCING", "All Cash — No Financing Contingency", { valueColor: NAVY, left: true }),
        gridCell("PROPOSAL VALID THROUGH", "[Date] at [Time] [Time Zone]"),
      ],
    }),
  ],
});

// Buyer — slim full-width bar below the grid, reading as a continuation of the
// same transaction summary rather than a separate card.
const buyerBar = new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: [Math.round(CONTENT_W * 0.22), Math.round(CONTENT_W * 0.78)],
  borders: { top: { style: BorderStyle.SINGLE, size: 3, color: BORDERGRAY }, bottom: { style: BorderStyle.NONE, size: 0, color: WHITE }, left: { style: BorderStyle.NONE, size: 0, color: WHITE }, right: { style: BorderStyle.NONE, size: 0, color: WHITE }, insideHorizontal: { style: BorderStyle.NONE, size: 0, color: WHITE }, insideVertical: { style: BorderStyle.NONE, size: 0, color: WHITE } },
  rows: [
    new TableRow({
      children: [
        new TableCell({
          width: { size: Math.round(CONTENT_W * 0.22), type: WidthType.DXA },
          margins: { top: 140, bottom: 130, left: 0, right: 120 },
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({ style: "TermLabel", spacing: { after: 0 }, children: [new TextRun({ text: "BUYER" })] })],
        }),
        new TableCell({
          width: { size: Math.round(CONTENT_W * 0.78), type: WidthType.DXA },
          margins: { top: 140, bottom: 130, left: 120, right: 0 },
          verticalAlign: VerticalAlign.CENTER,
          children: [new Paragraph({ children: [new TextRun({ text: "Oxford Realty Advisors or an affiliated entity designated prior to closing.", font: FONT, size: half(9), color: BLACK })] })],
        }),
      ],
    }),
  ],
});

const definitiveHeading = sectionHeading("DEFINITIVE AGREEMENT", 14);
const definitiveText = new Paragraph({
  style: "Body",
  children: [new TextRun({ text: "Upon acceptance of the above business terms, the parties will negotiate a mutually acceptable Purchase and Sale Agreement. Seller or Buyer may elect to prepare the initial draft. The PSA will contain customary provisions appropriate for the transaction." })],
});

// Non-binding — subtle information panel
const nonBindingBox = new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: [CONTENT_W],
  borders: hairlineBorder(BORDERGRAY, 4),
  rows: [
    new TableRow({
      children: [
        new TableCell({
          width: { size: CONTENT_W, type: WidthType.DXA },
          shading: { type: ShadingType.CLEAR, color: "auto", fill: LIGHTGRAY },
          margins: { top: 180, bottom: 180, left: 220, right: 220 },
          children: [
            new Paragraph({ style: "SectionHeading", spacing: { before: 0, after: pt(4) }, children: [new TextRun({ text: "NON-BINDING" })] }),
            new Paragraph({
              style: "Body",
              spacing: { after: 0 },
              children: [new TextRun({
                text: "This Acquisition Proposal is for discussion purposes only and is not intended to create a binding agreement or obligation on the part of either party. Neither party will be bound unless and until a definitive Purchase and Sale Agreement is executed by both parties.",
              })],
            }),
          ],
        }),
      ],
    }),
  ],
});

// Contact block
const contactBlock = new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: [CONTENT_W],
  borders: noBorders(),
  rows: [
    new TableRow({
      children: [
        new TableCell({
          width: { size: CONTENT_W, type: WidthType.DXA },
          margins: { top: 200, bottom: 0, left: 0, right: 0 },
          children: [
            new Paragraph({
              spacing: { after: pt(1) },
              children: [new TextRun({ text: "Gabriel Goldberg", font: FONT, size: half(11), bold: true, color: NAVY })],
            }),
            new Paragraph({
              style: "SmallBody",
              spacing: { after: pt(4) },
              children: [new TextRun({ text: "VP, Acquisitions — Oxford Realty Advisors", color: SLATE })],
            }),
            new Paragraph({
              style: "SmallBody",
              spacing: { after: 0 },
              children: [new TextRun({ text: "301.512.6125  |  ggoldberg@oxfordra.net  |  oxfordra.net" })],
            }),
          ],
        }),
      ],
    }),
  ],
});

// ---------- PAGE 2 ----------

const aboutHeading = new Paragraph({
  style: "SectionHeading",
  spacing: { before: 0, after: pt(4) },
  children: [new TextRun({ text: "ABOUT OXFORD REALTY ADVISORS", size: half(15) })],
});

const aboutSubtitle = new Paragraph({
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: GOLD, space: 6 } },
  spacing: { after: pt(12) },
  children: [new TextRun({ text: "A PRIVATE, LONG-TERM OWNER OF INDUSTRIAL REAL ESTATE", font: FONT, size: half(9.5), bold: true, color: SLATE, characterSpacing: pt(0.3) })],
});

const aboutText = new Paragraph({
  style: "Body",
  spacing: { after: pt(12), line: 260, lineRule: "auto" },
  children: [new TextRun({
    text: "Oxford Realty Advisors is a privately owned real estate investment company focused on shallow-bay industrial and flex properties. We are a direct principal buyer investing to own for the long term across multiple U.S. markets. Ownership is directly involved in every acquisition, allowing us to evaluate opportunities, make decisions, and move toward closing quickly.",
    size: half(9.25),
  })],
});

const whySellersHeading = sectionHeading("WHY SELLERS WORK WITH OXFORD", 10);

const whyItems = [
  ["PRIVATE CAPITAL", "Oxford invests private capital and does not require outside equity approval to acquire a property."],
  ["CERTAINTY OF EXECUTION", "Qualifying acquisitions can proceed on an all-cash basis, with no financing contingency."],
  ["DIRECT DECISION-MAKING", "Ownership is directly involved in every acquisition, allowing decisions to be made quickly."],
  ["LONG-TERM OWNERSHIP", "Oxford generally acquires with the intention of owning, operating, and improving a property for the long term."],
  ["FLEXIBLE UNDERWRITING", "Each property is evaluated on its own merits. Oxford is comfortable with vacancy, deferred maintenance, and other value-add situations."],
];

function whyCell(item) {
  if (!item) {
    return new TableCell({
      width: { size: Math.round(CONTENT_W * 0.5), type: WidthType.DXA },
      margins: { top: 0, bottom: 0, left: 0, right: 0 },
      children: [new Paragraph({ children: [new TextRun({ text: "" })] })],
    });
  }
  const [label, desc] = item;
  return new TableCell({
    width: { size: Math.round(CONTENT_W * 0.5), type: WidthType.DXA },
    margins: WHY_CELL_MARGINS,
    children: [
      new Paragraph({ spacing: { after: pt(2) }, children: [new TextRun({ text: label, font: FONT, size: half(9.5), bold: true, color: NAVY })] }),
      new Paragraph({ style: "SmallBody", spacing: { after: 0 }, children: [new TextRun({ text: desc })] }),
    ],
  });
}

const whyRows = [];
for (let i = 0; i < whyItems.length; i += 2) {
  whyRows.push(new TableRow({ children: [whyCell(whyItems[i]), whyCell(whyItems[i + 1])] }));
}
const whyTable = new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: [Math.round(CONTENT_W * 0.5), Math.round(CONTENT_W * 0.5)],
  borders: noBorders(),
  rows: whyRows,
});

const portfolioHeading = sectionHeading("OUR PORTFOLIO", 10);

// Confirmed figures per Gabriel, 2026-08-18: 500K+ SF / 140+ Tenants / 26 Properties / 3 Markets (OH/MD footprint — corrected from 7).
const stats = [
  ["500K+", "SF INDUSTRIAL & FLEX"],
  ["140+", "TENANTS"],
  ["26", "PROPERTIES"],
  ["3", "MARKETS"],
];
function statCell(stat, isLast) {
  const [num, label] = stat;
  return new TableCell({
    width: { size: Math.round(CONTENT_W * 0.25), type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, color: "auto", fill: LIGHTGRAY },
    margins: { top: 220, bottom: 220, left: 0, right: 0 },
    borders: isLast ? undefined : { right: { style: BorderStyle.SINGLE, size: 3, color: BORDERGRAY } },
    verticalAlign: VerticalAlign.CENTER,
    children: [
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: pt(2) }, children: [new TextRun({ text: num, font: FONT, size: half(22), bold: true, color: NAVY })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 0 }, children: [new TextRun({ text: label, font: FONT, size: half(7.5), bold: true, color: SLATE, characterSpacing: pt(0.2) })] }),
    ],
  });
}
const statsTable = new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: [Math.round(CONTENT_W * 0.25), Math.round(CONTENT_W * 0.25), Math.round(CONTENT_W * 0.25), Math.round(CONTENT_W * 0.25)],
  borders: noBorders(),
  rows: [new TableRow({ children: stats.map((s, i) => statCell(s, i === stats.length - 1)) })],
});

// Portfolio visual — three representative properties (replaces the placeholder
// box once real photography is available; see photos/ for source crops).
const PHOTO_DIR = path.join(__dirname, "photos");
const representativeProperties = [
  { file: "1100_rarig.jpg", caption: "Columbus, OH" },
  { file: "9050_redbranch.jpg", caption: "Columbia, MD" },
  { file: "55_newplant.jpg", caption: "Owings Mills, MD" },
];

const PHOTO_COL_W = Math.round(CONTENT_W / 3);
const IMG_W_PX = 214; // ~2.23in at 96dpi, fits the column with gutter
const IMG_H_PX = Math.round(IMG_W_PX / 1.5); // matches the 3:2 crop

function photoCell(item, position) {
  const data = fs.readFileSync(path.join(PHOTO_DIR, item.file));
  const leftMargin = position === "left" ? 0 : 90;
  const rightMargin = position === "right" ? 0 : 90;
  return new TableCell({
    width: { size: PHOTO_COL_W, type: WidthType.DXA },
    margins: { top: 0, bottom: 0, left: leftMargin, right: rightMargin },
    verticalAlign: VerticalAlign.TOP,
    children: [
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: pt(4) },
        children: [
          new ImageRun({
            data,
            type: "jpg",
            transformation: { width: IMG_W_PX, height: IMG_H_PX },
          }),
        ],
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 0 },
        children: [new TextRun({ text: item.caption, font: FONT, size: half(7.5), italics: true, color: SLATE })],
      }),
    ],
  });
}

const visualBox = new Table({
  width: { size: CONTENT_W, type: WidthType.DXA },
  columnWidths: [PHOTO_COL_W, PHOTO_COL_W, PHOTO_COL_W],
  borders: noBorders(),
  rows: [
    new TableRow({
      children: [
        photoCell(representativeProperties[0], "left"),
        photoCell(representativeProperties[1], "middle"),
        photoCell(representativeProperties[2], "right"),
      ],
    }),
  ],
});

const approachHeading = sectionHeading("OUR APPROACH", 12);
const approachText = new Paragraph({
  style: "Body",
  spacing: { after: 0 },
  children: [new TextRun({
    text: "Oxford focuses on functional industrial and flex real estate — buildings that work for tenants day to day, in markets where demand is driven by regional distribution, light manufacturing, and trade services. We look for situations where disciplined acquisition, attentive leasing, hands-on property management, and targeted capital improvements can create lasting value, and we hold what we buy for the long term.",
  })],
});

// ---------- Document assembly ----------

function footerPara() {
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    border: { top: { style: BorderStyle.SINGLE, size: 2, color: BORDERGRAY, space: 4 } },
    style: "Footer",
    children: [
      new TextRun({ text: "Oxford Realty Advisors  |  Acquisition Proposal      " }),
      new TextRun({ children: [PageNumber.CURRENT] }),
      new TextRun({ text: " / " }),
      new TextRun({ children: [PageNumber.TOTAL_PAGES] }),
    ],
  });
}

const doc = new Document({
  styles: { paragraphStyles },
  sections: [
    {
      properties: {
        page: {
          size: { width: PAGE_W, height: PAGE_H },
          margin: {
            top: MARGIN_TOP, bottom: MARGIN_BOTTOM, left: MARGIN_LEFT, right: MARGIN_RIGHT,
            header: HEADER_DIST, footer: FOOTER_DIST,
          },
        },
      },
      footers: { default: new Footer({ children: [footerPara()] }) },
      children: [
        companyName,
        proposalTitle,
        ...propertyRow,
        proposedTermsHeading,
        termsGrid,
        new Paragraph({ spacing: { before: pt(6), after: 0 }, children: [] }),
        buyerBar,
        definitiveHeading,
        definitiveText,
        new Paragraph({ spacing: { before: pt(10), after: 0 }, children: [] }),
        nonBindingBox,
        contactBlock,

        new Paragraph({ children: [new PageBreak()] }),

        aboutHeading,
        aboutSubtitle,
        aboutText,
        whySellersHeading,
        whyTable,
        portfolioHeading,
        statsTable,
        new Paragraph({ spacing: { before: pt(14), after: pt(8) }, children: [] }),
        visualBox,
        approachHeading,
        approachText,
      ],
    },
  ],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync("/home/claude/ora-proposal/Oxford Realty Advisors — Acquisition Proposal Template FINAL.docx", buffer);
  console.log("done");
});
