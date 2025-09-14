import logging
import os

import google.generativeai as genai


logger = logging.getLogger("google_api_wrapper")


class GoogleAPIWrapper:
    def __init__(self):
        """Initialize the Google API Wrapper."""
        self.api_key = os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is not set in the environment variables.")

        # Set up the Google API client
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model_name="gemini-1.5-flash")

    def generate_text(
        self, content: str, model: str = "text-bison-001", max_output_tokens: int = 256
    ):
        """Generate text using the Google Generative AI API.

        Args:
            content (str): The input content for text generation.
            model (str): The model to use for text generation.
            max_output_tokens (int): The maximum number of tokens in the output.

        Returns:
            str: The generated text.
        """
        if not isinstance(content, str):
            raise TypeError("content must be a string")
        if not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be a positive integer")

        try:
            generation_config = {"max_output_tokens": max_output_tokens}
            response = self.model.generate_content(
                contents=[content],
                generation_config=generation_config,  # Ensure proper formatting
            )
            return response.text
        except Exception as e:
            logger.error(f"Failed to generate text: {e}")
            raise

    def summarize_text(
        self, text: str, model: str = "text-bison-001", max_output_tokens: int = 256
    ):
        """Summarize text using the Google Generative AI API.

        Args:
            text (str): The text to summarize.
            model (str): The model to use for summarization.
            max_output_tokens (int): The maximum number of tokens in the summary.

        Returns:
            str: The summarized text.
        """
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        if not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be a positive integer")

        try:
            response = self.model.generate_content(
                contents=[text],  # Updated argument name to 'contents'
                max_output_tokens=max_output_tokens,
            )
            return response.text
        except Exception as e:
            logger.error(f"Failed to summarize text: {e}")
            raise

    def answer_question(self, question: str, max_output_tokens: int = 256):
        """Answer a question using the Google Generative AI API.

        Args:
            question (str): The question to answer.
            max_output_tokens (int): The maximum number of tokens in the answer.

        Returns:
            str: The answer to the question.
        """
        try:
            generation_config = {"max_output_tokens": max_output_tokens}
            response = self.model.generate_content(
                contents=[question], generation_config=generation_config
            )
            return response.text
        except Exception as e:
            logger.error(f"Failed to answer question: {e}")
            raise
