# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Natural language query parser for AI search."""

import re
from typing import Dict, List, Optional


class QueryParser:
    """Parse natural language queries into structured search parameters."""

    # Attribute patterns to extract from queries
    ATTRIBUTE_PATTERNS = {
        "female_protagonist": [
            r"female protagonist",
            r"women protagonist",
            r"female main character",
            r"heroine",
            r"strong female character",
        ],
        "male_protagonist": [
            r"male protagonist",
            r"male main character",
            r"hero",
        ],
        "author_gender_female": [
            r"by (a )?wom[ae]n",
            r"female author",
            r"women writer",
        ],
        "genre_romance": [
            r"love stor(y|ies)",
            r"romance",
            r"romantic",
        ],
        "genre_adventure": [
            r"adventure",
            r"quest",
        ],
        "genre_tragedy": [
            r"tragic",
            r"tragedy",
            r"tragedies",
        ],
        "theme_social_injustice": [
            r"social injustice",
            r"inequality",
            r"oppression",
        ],
        "theme_war": [
            r"about war",
            r"war stories",
            r"warfare",
        ],
        "era_victorian": [
            r"victorian",
            r"19th century",
        ],
    }

    # Map attributes to InvenioRDM subject search terms
    ATTRIBUTE_SUBJECT_MAPPING = {
        "female_protagonist": ["female", "women", "protagonist"],
        "male_protagonist": ["male", "protagonist"],
        "author_gender_female": ["women", "female"],
        "genre_romance": ["love", "romance"],
        "genre_adventure": ["adventure"],
        "genre_tragedy": ["tragedy", "tragic"],
        "theme_social_injustice": ["social", "injustice", "slavery"],
        "theme_war": ["war"],
        "era_victorian": ["victorian", "19th"],
    }

    def __init__(self):
        """Initialize query parser."""
        pass

    def parse(self, query: str) -> Dict:
        """Parse a natural language query.

        Args:
            query: Natural language query string

        Returns:
            Dictionary with parsed components:
            {
                "original_query": str,
                "intent": str,  # "search", "count", "list"
                "limit": int,
                "attributes": List[str],  # Detected attributes
                "search_terms": List[str],  # Subject search terms
                "semantic_query": str,  # Query for semantic search
            }
        """
        query_lower = query.lower().strip()

        result = {
            "original_query": query,
            "intent": self._parse_intent(query_lower),
            "limit": self._extract_limit(query_lower),
            "attributes": [],
            "search_terms": [],
            "semantic_query": query,
        }

        # Extract attributes
        for attr_name, patterns in self.ATTRIBUTE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    result["attributes"].append(attr_name)
                    # Add corresponding subject search terms
                    if attr_name in self.ATTRIBUTE_SUBJECT_MAPPING:
                        result["search_terms"].extend(
                            self.ATTRIBUTE_SUBJECT_MAPPING[attr_name]
                        )
                    break

        # Remove duplicates from search terms
        result["search_terms"] = list(set(result["search_terms"]))

        # Create semantic query (remove command words)
        semantic_query = query_lower
        command_words = ["show me", "find me", "get me", "give me", "list", "search for"]
        for cmd in command_words:
            semantic_query = semantic_query.replace(cmd, "")

        # Remove numbers
        semantic_query = re.sub(r'\d+', '', semantic_query)

        result["semantic_query"] = semantic_query.strip()

        return result

    def _parse_intent(self, query: str) -> str:
        """Determine query intent.

        Args:
            query: Lowercase query string

        Returns:
            Intent: "search", "count", "list"
        """
        if any(word in query for word in ["how many", "count", "number of"]):
            return "count"
        elif any(word in query for word in ["list all", "show all"]):
            return "list"
        else:
            return "search"

    def _extract_limit(self, query: str) -> Optional[int]:
        """Extract result limit from query.

        Args:
            query: Lowercase query string

        Returns:
            Integer limit or None
        """
        # Look for patterns like "3 books", "5 novels", "ten stories"
        number_words = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
        }

        # Try numeric
        match = re.search(r'(\d+)\s*(book|novel|stor|text|work)', query)
        if match:
            return int(match.group(1))

        # Try word numbers
        for word, num in number_words.items():
            if re.search(rf'{word}\s*(book|novel|stor|text|work)', query):
                return num

        return None

    def get_search_strategy(self, parsed_query: Dict) -> str:
        """Determine search strategy based on parsed query.

        Args:
            parsed_query: Result from parse()

        Returns:
            Strategy: "metadata", "semantic", "hybrid"
        """
        has_attributes = len(parsed_query["attributes"]) > 0
        has_search_terms = len(parsed_query["search_terms"]) > 0

        if has_attributes and has_search_terms:
            # Use metadata filtering + semantic ranking
            return "hybrid"
        elif has_search_terms:
            # Metadata search only
            return "metadata"
        else:
            # Pure semantic search
            return "semantic"


# Example usage and tests
if __name__ == "__main__":
    parser = QueryParser()

    test_queries = [
        "show me 3 books with female protagonists",
        "find novels by women",
        "get me 5 adventure stories",
        "books about social injustice",
        "how many Victorian novels are there?",
        "tragic love stories",
    ]

    print("Natural Language Query Parser - Test\n")
    print("=" * 60)

    for query in test_queries:
        result = parser.parse(query)
        strategy = parser.get_search_strategy(result)

        print(f"\nQuery: \"{query}\"")
        print(f"  Intent: {result['intent']}")
        print(f"  Limit: {result['limit']}")
        print(f"  Attributes: {result['attributes']}")
        print(f"  Search terms: {result['search_terms']}")
        print(f"  Semantic query: \"{result['semantic_query']}\"")
        print(f"  Strategy: {strategy}")
        print("-" * 60)
