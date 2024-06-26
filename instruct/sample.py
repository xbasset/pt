from instruct.instruct import Instruct
import logging
import datetime
import yaml

def write_output(filepath, output):
    with open(filepath, "w") as f:
        f.write(output)

def generate_sample_values(filepath, write_to_file=False, model=None, console=None):
    try:
        instruct = Instruct(filepath)
        template_values = instruct.template_values
        
        if len(template_values) == 0:
            # if no template values found in {filepath} just skip the generation
            return {}

        console.log(f"Generating sample values for {filepath}", f" with {model}" if model else "")
        sample_values_generator = Instruct("src/instructions/generate_sample_values.instruct", template=instruct.raw_template, values=instruct.template_values, forced_model=model)
        sample_values = sample_values_generator.run(temperature=0, max_tokens=1000)
        
        # parse the output to only keep the content of the "<output>"
        
        if write_to_file:
            try:
                # check if write_to_file is a valid filepath
                if write_to_file == True:
                    now = datetime.datetime.now()
                    output_filename = f"sample-{filepath.split('/')[-1].split('.')[0]}-{now.strftime('%Y-%m-%d.%H:%M:%S')}.txt"
                else:
                    output_filename = write_to_file
                    try:
                        with open(output_filename, "w") as f:
                            f.write("test")
                            f.truncate(0)
                    except:
                        raise ValueError(f"Invalid filepath: {output_filename}")
                    
                write_output(output_filename, sample_values)
                console.print(f"Sample values written to {output_filename}")
            except Exception as e:
                logging.error(f"Error writing sample values > {e}")

        # parse the sample values in a yaml file
        try:
            sample_values = yaml.load(sample_values.strip(), Loader=yaml.FullLoader)
        except Exception as e:
            logging.error(f"Error parsing sample values > 👀 possible cause: malformed sample values")
            # write sample values to a file
            write_output(f"sample-error-{filepath.split('/')[-1].split('.')[0]}.yaml", sample_values)
            logging.error(f"See raw sample values generation in `sample-error-{filepath.split('/')[-1].split('.')[0]}.yaml`")
            return None

        return sample_values
    
    except Exception as e:
        raise ValueError(f"{e}")


    

