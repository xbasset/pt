import jinja2
import re

from src.llm_engine.model import Model
import logging

logging.basicConfig(level=logging.ERROR)


class PT:
    """
    The PT class represents a Prompt Template.
    See the Prompt Template (PT) documentation for more details.

    Attributes:
        filepath (str): The filepath of the PT file.
        shebangs (list): A list of shebangs found in the PT file.
        template (jinja2.Template): The Jinja2 template object representing the PT file.
        models (list): Returns a list of model names extracted from the shebangs.
        tags (list): Returns a list of tags extracted from the template.
        template_values (list): Returns a list of jinja2 values extracted from the template.
        prompt (str): Returns the rendered prompt using the provided keyword arguments.

    Methods:
        _parse_file(): Parses the PT file and extracts shebangs and template.
        _perform_templating(**kwargs): Performs templating using the provided keyword arguments.
    """

    def __init__(self, filepath, forced_model=None, **kwargs):
        self.filepath = filepath

        try:
            from src.llm_engine.providers.model_loader import ModelLoader
            self.available_models, _ = ModelLoader().providers
        except Exception as e:
            logging.debug(
                f"{self.filepath} > available_models loading: {e}")
            self.available_models = None

        if forced_model is not None and self.available_models is not None:
            print(forced_model)
            for provider in self.available_models:
                if provider['model_name'] == forced_model:
                    self.forced_model: Model = provider['provider']
                    logging.info(f"Forced model: {forced_model}")
                    break
            if self.forced_model is None:
                logging.info(f"Forced model not found: {forced_model}")
        else:
            self.forced_model = None

        # store the other arguments for later use
        self.kwargs = kwargs
        self.shebangs = []
        self.template = None
        self.raw_template = None
        self._parse_file()

        from src.llm_engine.providers.model_loader import ModelLoader
        self.available_models = ModelLoader().providers
        self.models = [d['model_name'] for d in self.shebangs]
        

    @property
    def tags(self):
        """
        Extracts tags from the template.
        Tags are in the format: <tag_name>

        Returns:
            list: A list of tags extracted from the template.
        """
        return re.findall(r'(<[^>]*>)', self.raw_template)

    @property
    def template_values(self):
        """
        Extracts jinja2 values from the template.
        Jinja2 values are in the format: {{ value }}

        Returns:
            list: A list of jinja2 values extracted from the template.
        """
        return list(set(re.findall(r'{{([^}]*)}}', self.raw_template)))

    @property
    def prompt(self):
        """
        Returns the rendered prompt using the provided keyword arguments.

        Args:
            **kwargs: Keyword arguments to be used for templating.

        Returns:
            str: The rendered prompt.
        """

        if self.forced_model is not None:
            logging.info(
                f"Prompt template resolved with forced_model: {self.forced_model.name}")
            return self._perform_templating(**self.kwargs, model=self.forced_model)
        elif self.matching_model is not None:
            return self._perform_templating(**self.kwargs, model=self.matching_model.name)
        else:
            return self._perform_templating(**self.kwargs)

    @property
    def matching_model(self) -> Model:
        # return the first available model matching with the shebangs
        try:
            selected_model = None
            # logging.info(f"available models: {self.available_models}")
            for model in self.models:
                for provider in self.available_models:
                    # logging.info(f"Checking provider: {provider['model_name']}")
                    if provider['model_name'] == model:
                        selected_model = provider['provider']
                        break

                if selected_model is not None:
                    break

            return selected_model
        except Exception as e:
            logging.error(f"Error finding matching model: {e}")
            return None

    def _parse_file(self):
        """
        Parses the PT file and extracts shebangs and template.
        """
        try:
            with open(self.filepath, 'r') as file:
                lines = file.readlines()
                i = 0
                # find all the shebangs and get their values
                while lines[i].startswith("#!"):
                    shebang = lines[i].strip()
                    match = re.search(r'#!\s*([^/]*)/?([^/]*)?', shebang)
                    if match is not None:
                        model_name, version = match.groups()
                        self.shebangs.append({
                            'model_name': model_name,
                            'version': version if version else 'latest'
                        })
                    else:
                        raise ValueError(
                            f"Invalid shebang: {shebang}\nFormat: #! model_name(/version)")
                    i += 1
                # find the first non empty line after shebangs
                while not lines[i].strip():
                    i += 1
                # remove all the empty lines at the end of the file
                while not lines[-1].strip():
                    lines.pop()

                self.raw_template = ''.join(lines[i:])
                self.template = jinja2.Template(self.raw_template)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"File not found: {self.filepath}")
        except Exception as e:
            raise Exception(f"Error parsing file: {self.filepath} - {e}")

    def _perform_templating(self, **kwargs):
        """
        Performs templating using the provided keyword arguments.

        Args:
            **kwargs: Keyword arguments to be used for templating.

        Returns:
            str: The rendered template.
        """
        # if one of the args is of type PT, call its prompt method
        for k, v in kwargs.items():
            if isinstance(v, PT):
                kwargs[k] = v.prompt
                # also retrieve the models from the PT and choose the common model with the current PT
                self.models = list(set(self.models).intersection(v.models))

        try:
            return self.template.render(**kwargs)
        except Exception as e:
            logging.error(f"Error performing templating: {e}")
            logging.error(
                f"Check that you passed all the template values: {self.template_values}")
            return None

    def __str__(self):
        """
        Returns a string representation of the PT object.

        Returns:
            str: A string representation of the PT object.
        """
        return f"PT: {self.filepath}"

    def run(self, **kwargs):
        """
        Run the prompt to the appropriate model.

        Returns:
            str: The result of the Model call.
        """
        try:
            # for each model in the shebangs, in order, check if there is a provider for it
            # if there is, call it with the prompt

            if self.forced_model is not None:
                logging.info(
                    f"Running prompt with forced model: {self.forced_model.name}")
                return self.forced_model.invoke_from_pt(self, **kwargs)[0]

            elif self.matching_model is not None:
                logging.info(f"run with args: {kwargs}")
                return self.matching_model.invoke_from_pt(self, **kwargs)[0]
            else:
                raise Exception(f"""
{self} > No matching provider <> model found:
providers: {self.available_models}
PT's compatibility list: {self.models}
To fix the problem:
1. Check the providers in the models.conf file.
2. Check the PT file's shebangs for compatibility with the providers.""")

        except Exception as e:
            logging.error(f"Error running PT: {self} > {e}")
            return None