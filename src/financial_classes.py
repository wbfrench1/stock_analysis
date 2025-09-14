# Assuming you have the XBRLClient class in xbrl_client.py
from typing import List, Dict, Any
import pandas as pd
from xbrl_client import XBRLClient

# Standard roles to identify the presentation network for the Income Statement
PRESENTATION_LINK_NAME = "presentationLink"
INCOME_STATEMENT_ROLES = [
    "Statement - Consolidated Statements of Operations",
    "Statement of Operations",
    "Consolidated Statements of Income",
    "Consolidated Statements of Operations",
    "Consolidated Statements of Earnings",
    "Statements of Consolidated Income"
]

class FinancialStatement:
    """
    Represents a specific financial statement, storing its concepts,
    facts, and providing methods to combine them.
    """
    def __init__(self, statement_type: str):
        self.statement_type = statement_type
        self.concepts: List[Dict[str, Any]] = []
        self.facts: List[Dict[str, Any]] = []

    def add_concepts(self, new_concepts: List[Dict[str, Any]]):
        """Adds a list of new concepts to the statement."""
        self.concepts.extend(new_concepts)

    def add_facts(self, new_facts: List[Dict[str, Any]]):
        """Adds a list of new facts to the statement."""
        self.facts.extend(new_facts)

    def combine_to_dataframe(self) -> pd.DataFrame:
        """
        Combines concept relationships and facts into a single DataFrame,
        similar to your final code block.
        """
        if not self.concepts or not self.facts:
            print("Concepts or facts are missing. Cannot create DataFrame.")
            return pd.DataFrame()

        # Your original merge logic
        df_concepts = pd.DataFrame(self.concepts)
        df_concepts.to_csv('output/concepts.csv')
        df_facts = pd.DataFrame(self.facts)
        df_facts.to_csv('output/facts.csv')
        
        # We'll rename columns for a cleaner merge
        df_concepts.rename(columns={'relationship.target-concept-id': 'concept.id'}, inplace=True)
        
        # Merge the two DataFrames on the concept ID
        merged_df = df_concepts.merge(
            df_facts.drop_duplicates(),
            how='left',
            on='concept.id'
        )
        
        # Sort by tree-sequence to maintain the presentation order
        return merged_df.sort_values(by=['relationship.tree-sequence', 'relationship.tree-depth'])

    def __repr__(self):
        return (f"FinancialStatement(type='{self.statement_type}', "
                f"num_concepts={len(self.concepts)}, num_facts={len(self.facts)})")

# ---

class Report:
    """Represents a single 10-K report filing."""
    def __init__(self, data: Dict[str, Any]):
        # ... (same as before)
        self.report_id = data.get('report.id')
        self.dts_id = data.get('dts.id')
        self.fiscal_year = data.get('report.year-focus')
        self.filing_date = data.get('report.filing-date')
        self.period_end = data.get('report.period-end')
        self.is_most_current = data.get('report.is-most-current')
        self.entity_name = data.get('report.entity-name')
        self.entry_url = data.get('report.entry-url')
        self.statements: Dict[str, FinancialStatement] = {}
        
    def _find_financial_statement_network(self, client: XBRLClient, statement_type: str) -> str:
        """
        Finds the network ID for a given financial statement type (e.g., "Income Statement").
        (Based on your first code block)
        """
        print(f"  - Searching for '{statement_type}' network...")
        
        # Use a list of role descriptions for the search
        if statement_type == "Income Statement":
            roles = INCOME_STATEMENT_ROLES
        else:
            # You could add other statement types here (Balance Sheet, etc.)
            print(f"  - Warning: Role descriptions for '{statement_type}' are not defined.")
            return None

        network_search_params = {
            "dts.id": self.dts_id,
            "network.link-name": PRESENTATION_LINK_NAME,
            "network.role-description": ",".join(roles),
            "fields": "network.id,network.role-description"
        }
        
        try:
            response_data = client.query(f"dts/{self.dts_id}/network/search", params=network_search_params)
            networks_data = response_data.get('data', [])

            if networks_data:
                # Sort to get the most specific role description (e.g., 'Consolidated Statements of Operations')
                networks_data.sort(key=lambda x: len(x.get('network.role-description', '')), reverse=True)
                network_id = networks_data[0].get('network.id')
                print(f"  - Found network ID {network_id} for '{statement_type}'.")
                return network_id
            else:
                print(f"  - No network found for '{statement_type}'.")
                return None
        except Exception as e:
            print(f"  - Error searching for network: {e}")
            return None
    
    def _load_concepts_and_relationships(self, client: XBRLClient, network_id: str) -> List[Dict[str, Any]]:
        """
        Loads all concepts and their relationships for a given network ID.
        (Based on your second code block)
        """
        print(f"  - Loading concepts and relationships from network {network_id}...")
        relationships_params = {
            "dts.id": self.dts_id,
            "network.id": network_id,
            "network.arcrole-uri": "http://www.xbrl.org/2003/arcrole/parent-child",
            "fields": (
                "relationship.target-concept-id,relationship.source-name,"
                "relationship.target-namespace,relationship.preferred-label,"
                "relationship.tree-depth,relationship.tree-sequence,relationship.target-name.sort(ASC)"
            ),
            
        }
        
        try:
            response_data = client.query("relationship/search", params=relationships_params)
            return response_data.get('data', [])
        except Exception as e:
            print(f"  - Error loading relationships: {e}")
            return []

    def load_income_statement_data(self, client: XBRLClient):
        """
        Orchestrates the entire process of finding the network, loading concepts,
        loading facts, and storing them in the FinancialStatement object.
        """
        print('in the load_income_statement_data functions')
        # Step 1: Find the Network ID
        network_id = self._find_financial_statement_network(client, "Income Statement")
        if not network_id:
            return
        print('found the financial statement network')

        # Step 2: Load concepts and relationships
        concepts_data = self._load_concepts_and_relationships(client, network_id)
        if not concepts_data:
            return
        print('loaded the concepts and relationships')

        # Step 3: Extract a list of concept local-names to use for fact retrieval
        concept_names = {c.get('relationship.target-name') for c in concepts_data if c.get('relationship.target-name')}
        concept_names.update({c.get('relationship.source-name') for c in concepts_data if c.get('relationship.source-name')})
        
        
        # Step 4: Load the facts based on the discovered concepts
        statement = FinancialStatement("Income Statement")
        statement.add_concepts(concepts_data)
        page_size = 100
        offset = 0

        fact_fields = [
            'fact.value', 'concept.id.sort(ASC)','concept.is-base', 'concept.local-name','dimensions.count.sort(ASC)',
            'period.fiscal-year.sort(DESC)', 'period.fiscal-period', 
            'unit.local-name', 'dimension.local-name', 'member.local-name', 
            'report.acceptedtimestamp.sort(DESC)'
        ]

        while True:
            print('start querying fact data')
            params = {
                'report.id': self.report_id,
                'dimensions.count' : '0',
                #'concept.local-name': ','.join(concept_names),
                #'aspect.dei:LegalEntityAxis': 'dei:LegalEntityConsolidatedMember',
                
                'fields': ','.join(fact_fields + [f',fact.offset({offset})'])   
            }
            try:
                #print('params: ', params)
                response_data = client.query(endpoint= "fact/search?unique", params=params)
                facts_data = response_data.get('data', [])
                if not facts_data:
                    print ("No facts data")
                    break
                statement.add_facts(facts_data)
                if len(facts_data) < page_size:
                    break
                offset += page_size
                print('offset:', offset)
            except Exception as e:
                print()
                print(f"  - Error loading facts: {e}")
                break
        
        self.statements['Income Statement'] = statement
        print(f"  - Finished loading facts. Found {len(statement.facts)} total facts.")


class Company:
    """Represents a company and its financial filings."""
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.reports: Dict[str, Report] = {}
        
    def load_10k_reports(self, client: Any, years: List[str]):
        """
        Queries the API to find and load 10-K reports for the specified years.
        
        Args:
            client (XBRLClient): An instance of the XBRLClient.
            years (List[str]): A list of fiscal years as strings (e.g., ['2023', '2024']).
        """
        
        report_fields = [
            'report.id',
            'dts.id',
            'report.year-focus',
            'report.filing-date',
            'report.period-end',
            'report.is-most-current',
            'report.entity-name',
            'report.entry-url'
        ]

        params = {
            'entity.ticker': self.ticker,
            'report.document-type': '10-K',
            'report.year-focus': ','.join(years),
            # Your original code had this, it's good for ensuring we get the report data.
            'fields': ','.join(report_fields) + f',report.limit({len(years)})'
        }
        
        print(f"Loading 10-K reports for {self.ticker} for years {years}...")
        
        try:
            response_data = client.query('report/search', params=params)
            reports_data = response_data.get('data', [])

            for report_dict in reports_data:
                report = Report(report_dict)
                # Store the report in the company's reports dictionary by fiscal year
                self.reports[report.fiscal_year] = report
            
            print(f"Successfully loaded {len(self.reports)} reports for {self.ticker}.")
            print('dts.id', report.dts_id)
            print('report.id', report.report_id)
        
        except Exception as e:
            print(f"Failed to load reports for {self.ticker}: {e}")

    def __repr__(self):
        return f"Company(ticker='{self.ticker}', loaded_reports={list(self.reports.keys())})"