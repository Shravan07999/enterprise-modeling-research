from sqlmodel import Session, select, delete
from database import engine, create_db_and_tables
from models import Prompt, Chain, ChainStep, User, UserRole
import json


def seed_data():
    with Session(engine) as session:
        print("Clearing existing database records...")
        session.exec(delete(ChainStep))
        session.exec(delete(Chain))
        session.exec(delete(Prompt))
        session.commit()

        # Instructions for Visual JSON
        visual_instruction = """
        IMPORTANT: At the end of your response, you MUST include a JSON block for the visual diagram.
        The `nodes` and `edges` lists MUST BE POPULATED with the actual entities and relationships you described.
        
        Example JSON Structure:
        ```json
        {
          "visual_flow": {
            "nodes": [
              { "id": "n1", "data": { "label": "ENTITY NAME" }, "position": { "x": 0, "y": 0 } }
            ],
            "edges": [
              { "id": "e1", "source": "n1", "target": "n2", "label": "RELATIONSHIP" }
            ]
          }
        }
        ```
        """

        # 1. Shared Prompts
        p_context = Prompt(
            name="Context Extraction & Normalization",
            description="Extracts actors, goals, processes, and objects.",
            template="""Analyze the following enterprise scenario and extract entities.
            Scenario: {{scenario}}
            Output strictly in JSON: actors, goals, processes, objects, constraints.""",
            input_variables="scenario",
            tags="shared",
        )
        p_critic = Prompt(
            name="Critic & Validation",
            description="Senior architect review.",
            template="""Act as a senior modeling critic. Review the following architectural model for consistency.
            Model Content: {{previous_step_output}}
            List Critical Issues and Suggestions.""",
            input_variables="framework,previous_step_output",
            tags="shared",
        )
        session.add(p_context)
        session.add(p_critic)
        session.commit()

        # 2. 4EM Framework (Using persistent context)
        p_4em_goal = Prompt(
            name="4EM Goal Model",
            template="""Generate a detailed 4EM Goal Model based on the extracted context.
            Raw Context: {{context_extraction}}
            Previous Analysis: {{previous_step_output}}
            - Define a clear goal hierarchy.
            - Assign responsible Actors.""",
            input_variables="context_extraction,previous_step_output",
            tags="4em",
        )
        p_4em_process = Prompt(
            name="4EM Process Model",
            template=f"""Generate a detailed 4EM Process Model. 
            Raw Context: {{context_extraction}}
            - Describe the end-to-end workflow activities.
            - Identify Actors for each step.
            
            {visual_instruction}""",
            input_variables="context_extraction,previous_step_output",
            tags="4em",
        )
        session.add(p_4em_goal)
        session.add(p_4em_process)

        # 3. TOGAF Framework
        p_togaf_vision = Prompt(
            name="TOGAF Architecture Vision",
            template="""Develop a TOGAF Architecture Vision (Phase A).
            Raw Context: {{context_extraction}}
            - Define Problem Statement and Strategic Value.""",
            input_variables="context_extraction,previous_step_output",
            tags="togaf",
        )
        p_togaf_business = Prompt(
            name="TOGAF Business Architecture",
            template=f"""Develop the TOGAF Business Architecture (Phase B).
            Raw Context: {{context_extraction}}
            Vision Analysis: {{previous_step_output}}
            - Define Business Services and Organization Units.
            
            {visual_instruction}""",
            input_variables="context_extraction,previous_step_output",
            tags="togaf",
        )
        session.add(p_togaf_vision)
        session.add(p_togaf_business)

        # 4. ArchiMate Framework
        p_archimate_layers = Prompt(
            name="ArchiMate Layering",
            template="""Map the architecture into ArchiMate Layers:
            Raw Context: {{context_extraction}}
            1. Business Layer
            2. Application Layer
            3. Technology Layer""",
            input_variables="context_extraction,previous_step_output",
            tags="archimate",
        )
        p_archimate_rels = Prompt(
            name="ArchiMate Relationship Mapping",
            template=f"""Define the ArchiMate Relationships between the layers.
            Raw Context: {{context_extraction}}
            Layering Analysis: {{previous_step_output}}
            
            {visual_instruction}""",
            input_variables="context_extraction,previous_step_output",
            tags="archimate",
        )
        session.add(p_archimate_layers)
        session.add(p_archimate_rels)

        # 5. Zachman Framework
        p_zachman_matrix = Prompt(
            name="Zachman Matrix",
            template="""Produce a Zachman Matrix mapping (6x6).
            Raw Context: {{context_extraction}}
            - Fill What, How, Where, Who, When, Why.""",
            input_variables="context_extraction,previous_step_output",
            tags="zachman",
        )
        p_zachman_perspectives = Prompt(
            name="Zachman Perspectives",
            template=f"""Normalize for Planner, Owner, and Designer perspectives.
            Raw Context: {{context_extraction}}
            Matrix Analysis: {{previous_step_output}}
            
            {visual_instruction}""",
            input_variables="context_extraction,previous_step_output",
            tags="zachman",
        )
        session.add(p_zachman_matrix)
        session.add(p_zachman_perspectives)

        session.commit()

        # --- Chains ---
        def add_steps(chain, prompts):
            for i, p in enumerate(prompts, 1):
                mapping = {}
                if i > 1:
                    mapping["previous_step_output"] = "result"
                    mapping["context_extraction"] = "context_extraction"
                session.add(
                    ChainStep(
                        chain_id=chain.id,
                        prompt_id=p.id,
                        order=i,
                        input_mapping=json.dumps(mapping) if mapping else None,
                    )
                )

        # 4EM
        c_4em = Chain(
            name="4EM Enterprise Alignment",
            description="Goal-oriented alignment.",
            framework="4EM",
        )
        session.add(c_4em)
        session.commit()
        add_steps(c_4em, [p_context, p_4em_goal, p_4em_process, p_critic])

        # TOGAF
        c_togaf = Chain(
            name="TOGAF ADM Cycle",
            description="Standard ADM phases.",
            framework="TOGAF",
        )
        session.add(c_togaf)
        session.commit()
        add_steps(c_togaf, [p_context, p_togaf_vision, p_togaf_business, p_critic])

        # ArchiMate
        c_archimate = Chain(
            name="ArchiMate Layering",
            description="Layered view of the enterprise.",
            framework="ArchiMate",
        )
        session.add(c_archimate)
        session.commit()
        add_steps(
            c_archimate, [p_context, p_archimate_layers, p_archimate_rels, p_critic]
        )

        # Zachman
        c_zachman = Chain(
            name="Zachman Matrix",
            description="Comprehensive classification.",
            framework="Zachman",
        )
        session.add(c_zachman)
        session.commit()
        add_steps(
            c_zachman, [p_context, p_zachman_matrix, p_zachman_perspectives, p_critic]
        )

        session.commit()
        print("Framework seed completed successfully (4EM, TOGAF, ArchiMate, Zachman).")


if __name__ == "__main__":
    create_db_and_tables()
    seed_data()
