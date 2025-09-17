"""
Image generation tool using Vertex AI Imagen for technical diagrams and architecture visualizations.
"""

import os
import google.auth
from google import genai
from google.genai import types
from google.adk.tools import ToolContext
from .diagram_generator_tool import generate_diagram_with_code


# Set up Vertex AI environment
_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-ec92c6095411")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "europe-west4")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

# Configure the genai client
client = genai.Client(vertexai=True)


async def generate_technical_image(prompt: str, tool_context: ToolContext):
    """Generate technical architecture diagrams using ASCII diagrams + Imagen enhancement."""
    try:
        # Get ASCII diagram first for structure
        ascii_result = await generate_diagram_with_code(prompt, tool_context)

        if ascii_result["status"] == "success":
            # Now enhance the ASCII diagram with Imagen
            ascii_description = ascii_result.get("diagram_code", "ASCII diagram generated")

            enhanced_prompt = f"""Create a professional technical architecture diagram based on this ASCII structure:

{ascii_description}

STYLE: Clean, modern cloud architecture diagram with official provider icons and colors.
LAYOUT: Follow the ASCII structure but make it visually appealing.
ICONS: Use official cloud provider icons - Azure blue (#0078D4), GCP colors, AWS orange.
FORMAT: Professional technical documentation style with clear labels."""

            response = client.models.generate_images(
                model="imagen-4.0-generate-001",
                prompt=enhanced_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="16:9",
                    safety_filter_level="block_low_and_above",
                    person_generation="allow_adult",
                ),
            )

            if response.generated_images is not None:
                for generated_image in response.generated_images:
                    image_bytes = generated_image.image.image_bytes
                    artifact_name = f"enhanced_technical_diagram.png"

                    report_artifact = types.Part.from_bytes(
                        data=image_bytes, mime_type="image/png"
                    )

                    await tool_context.save_artifact(artifact_name, report_artifact)

                    return {
                        "status": "success",
                        "message": f"Enhanced technical diagram created based on ASCII structure for: {prompt}",
                        "artifact_name": artifact_name,
                        "method": "ascii_enhanced",
                        "ascii_structure": ascii_description
                    }

        # Fallback to Imagen if programmatic generation fails
        enhanced_prompt = f"""Professional technical architecture diagram: {prompt}

STYLE: Clean, modern cloud architecture diagram with official provider icons and colors.
LAYOUT: Logical component grouping with clear data flow arrows.
ICONS: Use official cloud provider icons - Azure blue (#0078D4), GCP colors, AWS orange.
FORMAT: Professional technical documentation style with clear labels."""

        response = client.models.generate_images(
            model="imagen-4.0-generate-001",
            prompt=enhanced_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9",
                safety_filter_level="block_low_and_above",
                person_generation="allow_adult",
            ),
        )

        if response.generated_images is not None:
            for generated_image in response.generated_images:
                image_bytes = generated_image.image.image_bytes
                artifact_name = f"technical_diagram.png"

                report_artifact = types.Part.from_bytes(
                    data=image_bytes, mime_type="image/png"
                )

                await tool_context.save_artifact(artifact_name, report_artifact)

                return {
                    "status": "success",
                    "message": f"Technical diagram generated with Imagen for: {prompt}",
                    "artifact_name": artifact_name,
                    "method": "imagen_fallback"
                }
        else:
            return {
                "status": "error",
                "message": f"Both programmatic and Imagen generation failed. Response: {str(response)}",
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to generate image: {str(e)}"
        }