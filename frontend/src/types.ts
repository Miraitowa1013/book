export type Section = {
  name: string;
  content: string;
};

export type OcrResponse = {
  resumeId: number;
  extractedTextPreview: string;
  sections: Section[] | any;
};

export type SuggestionsItem = {
  name: string;
  issues: string[];
  recommendations: string[];
  rewrite_example?: string;
};

export type SuggestionsResponse = {
  resumeId: number;
  overall_summary: string;
  items: SuggestionsItem[];
};

