import re
import yaml
import tiktoken
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
import os


class InterviewAgent:
    def __init__(self, config: dict):
        """初始化 OpenAI API"""
        self.client = OpenAI(
            api_key=config['api_key'],
            base_url=config.get('base_url', "https://vip.apiyi.com/v1")
        )
        with open('prompts.yaml', 'r', encoding='utf-8') as file:
            self.prompts = yaml.safe_load(file)

        self.model = config.get('model', 'gpt-4o')
        self.interviewee_name = config['interviewee_name']
        self.temperature = config.get('temperature', 0.7)
        self.revise_iteration = config.get('revise_iteration', 1)
        self.chunk_size = config.get('chunk_size', 5000)
        # 获取transcript_system_prompt
        self.refinement_system_prompt = self.prompts['refinement_system_prompt']

        self.refined_introduction = self.refine_introduction(config['interviewee_introduction'])

        self.transcript_system_prompt = self.prompts['transcript_system_prompt'].format(
            interviewee_name=self.interviewee_name,
            interviewee_introduction=self.refined_introduction
        )

    def revise_text(self, unrevised_text: str) -> str:
        """调用 OpenAI API 进行对话"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.transcript_system_prompt},
                    {"role": "user", "content": unrevised_text}
                ],
                temperature=self.temperature,
            )
            return response.choices[0].message.content
        
        except Exception as e:
            print(f"API 调用出错: {str(e)}")
            return None
        
    
    def refine_introduction(self, interviewee_introduction: str) -> str:
        """优化被采访者的自我介绍"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.prompts['refinement_system_prompt']},
                    {"role": "user", "content": interviewee_introduction}
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content
        
        except Exception as e:
            print(f"API 调用出错: {str(e)}")
            return None

    def check_difference(self, unrevised_text: str, revised_text: str) -> str:
        """检查润色前后的文本差异"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.prompts['check_difference_system_prompt']},
                    {"role": "user", "content": f"润色前文本: {unrevised_text}\n润色后文本: {revised_text}"}
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content 
        
        except Exception as e:
            print(f"API 调用出错: {str(e)}")
            return None

    def supply_missing_information(self, unrevised_text: str, revised_text: str, difference_information: str) -> str:
        """补充润色前文本中遗漏的信息"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.prompts['supply_missing_information_system_prompt']},
                    {"role": "user", "content": self.prompts['supply_missing_information_user_prompt'].format(
                        unrevised_text=unrevised_text,
                        revised_text=revised_text,
                        difference_information=difference_information
                    )}
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content 
        
        except Exception as e:
            print(f"API 调用出错: {str(e)}")
            return None
    
    def iterative_process_text(self, unrevised_text:str) -> str:
        """处理文本的主流程"""
        try:
            # 第一次润色
            revised_text = self.revise_text(unrevised_text)
            print("第一次润色结果：", revised_text)
            if revised_text is None:
                return None
                
            # 多次迭代润色和检查
            for i in range(self.revise_iteration):
                # 检查差异
                difference = self.check_difference(unrevised_text, revised_text)
                print(difference)
                if difference is None:
                    return revised_text
                    
                # 补充遗漏信息
                revised_text = self.supply_missing_information(
                    unrevised_text,
                    revised_text, 
                    difference
                )
                print("补充遗漏信息结果：", revised_text)
                if revised_text is None:
                    return None
                    
            return revised_text
        
            
        except Exception as e:
            print(f"处理文本出错: {str(e)}")
            return None

    def remove_time_from_string(self,text:str) -> str:
        # 使用正则表达式匹配时间格式并替换为空字符串
        cleaned_text = re.sub(r'\(\d{2}:\d{2}:\d{2}\)', '', text)
        return cleaned_text.strip()  # 去掉前后的空格

    def replace_speaker(self, text:str, interviewee_name:str) -> str:
        speaker, content = text.split(': ', 1)
        if speaker != interviewee_name:
            speaker = "蜗壳进阶联盟"
        
        return f"{speaker}: {content}"

    def read_file_to_list(self, file_path:str) -> list:
        with open(file_path, 'r', encoding='utf-8') as file:
            # 读取所有行并去掉换行符
            lines = [line.strip() for line in file.readlines() if line.strip()]
        return lines
    
    def convert_format(self,file_path:str) -> str:
        content_list = self.read_file_to_list(file_path)
        content_list = [self.remove_time_from_string(line) for line in content_list]
        content_list = [self.replace_speaker(line, self.interviewee_name) for line in content_list]
        content_list = self.merge_consecutive_speakers(content_list)

        return content_list
    
    def chunk_text(self, content_list:list) -> list:
        chunks = []
        single_chunk = ""
        for line in content_list:
            if len(single_chunk) + len(line) > self.chunk_size:
                chunks.append(single_chunk)
                single_chunk = ""
            single_chunk += line
        if single_chunk:
            chunks.append(single_chunk)

        return chunks
    
    def count_tokens(self, text):
        encoding = tiktoken.encoding_for_model(self.model)
        tokens = encoding.encode(text)
        return len(tokens)
    
    def merge_consecutive_speakers(self, dialogue_list:list) -> list:
        if not dialogue_list:
            return []
        merged = []
        current_speaker = None
        current_content = ""
        
        for line in dialogue_list:
            speaker, content = line.split(': ', 1)
            
            if speaker == current_speaker:
                current_content += ' ' + content
            else:
                # 如果是新的说话人，保存之前的内容并开始新的
                if current_speaker:
                    merged.append(f"{current_speaker}: {current_content}")
                current_speaker = speaker
                current_content = content
    
        if current_speaker:
            merged.append(f"{current_speaker}: {current_content}")
        paired_dialogue = []
        for i in range(0, len(merged)-1, 2):
            if i+1 < len(merged):
                paired_dialogue.append(merged[i] + '\n' + merged[i+1])
            else:
                paired_dialogue.append(merged[i] + "")
        
        return paired_dialogue
    
    def iterative_process_text_list(self, text_list:list) -> list:
        revised_text_list = []
        for text in text_list:
            revised_text = self.iterative_process_text(text)
            revised_text_list.append(revised_text)
        return revised_text_list
    
    def process_text_standalone(self, text):
        """独立的处理函数"""
        return self.iterative_process_text(text)
    
    def multiprocess_iterative_process_text_list(self, text_list: list) -> list:
        """使用线程池处理文本列表"""
        with ThreadPoolExecutor(max_workers=4) as executor:
            revised_text_list = list(executor.map(self.iterative_process_text, text_list))
        return revised_text_list
    
    def revise(self, file_path:str, output_path:str):
        converted_format_text = self.convert_format(file_path=file_path)
        chunked_list = self.chunk_text(content_list=converted_format_text)
        revised_result = self.multiprocess_iterative_process_text_list(text_list=chunked_list)
        final_result = ''
        for single_result in revised_result:
            final_result += single_result
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(final_result)

if __name__ == "__main__":
    with open('config.yaml', 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    
    # 确保输出目录存在
    output_dir = os.path.dirname(config['output_file'])
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    Agent = InterviewAgent(config)
    Agent.revise(
        file_path=config['input_file'],
        output_path=config['output_file']
    )