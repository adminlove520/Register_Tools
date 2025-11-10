import time
import random
import re
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import json

# 配置日志
import sys

# 修复Unicode编码问题
class UnicodeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            if hasattr(stream, 'buffer'):
                stream.buffer.write(msg.encode('utf-8') + b'\n')
            else:
                stream.write(msg + '\n')
            self.flush()
        except Exception:
            self.handleError(record)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("register.log", encoding='utf-8'),
        UnicodeStreamHandler(sys.stdout)
    ]
)

# 生成随机中文昵称
def generate_chinese_name(length=3):
    # 中文字符范围
    start, end = 0x4e00, 0x9fa5
    return ''.join([chr(random.randint(start, end)) for _ in range(length)])

# 生成随机8位密码
def generate_password():
    chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*'
    return ''.join([random.choice(chars) for _ in range(8)])

# 获取临时邮箱
def get_temp_email(driver):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 打开临时邮箱网站
            logging.info(f"尝试访问临时邮箱网站 (尝试 {attempt+1}/{max_retries})")
            driver.set_page_load_timeout(30)
            driver.get('http://mail0.dfyx.xyz/')
            
            # 等待页面加载完成
            WebDriverWait(driver, 20).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            time.sleep(2)
            
            # 尝试多种方式点击刷新按钮
            refresh_clicked = False
            try:
                # 方式1: 通过ID查找
                refresh_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, 'refreshShortid'))
                )
                refresh_button.click()
                logging.info("成功点击刷新按钮 (通过ID)")
                refresh_clicked = True
            except Exception as e:
                logging.warning(f"通过ID点击刷新按钮失败: {e}")
                try:
                    # 方式2: 通过其他选择器查找
                    refresh_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(@id, 'refresh')]"))
                    )
                    refresh_button.click()
                    logging.info("成功点击刷新按钮 (通过XPATH)")
                    refresh_clicked = True
                except Exception as e2:
                    logging.error(f"通过XPATH点击刷新按钮也失败: {e2}")
            
            if refresh_clicked:
                time.sleep(2)
            
            # 尝试多种方式获取邮箱地址
            # 方式1: 查找包含邮箱的按钮或文本元素
            email_elements = driver.find_elements(By.XPATH, "//button | //div | //span")
            for element in email_elements:
                try:
                    text = element.text.strip()
                    if '@' in text and len(text) > 5:
                        # 提取邮箱格式文本
                        email_match = re.search(r'\S+@\S+', text)
                        if email_match:
                            email = email_match.group(0)
                            logging.info(f"成功获取邮箱地址: {email}")
                            return email
                except Exception:
                    continue
            
            # 方式2: 查找特定class的元素
            email_containers = driver.find_elements(By.CLASS_NAME, 'ui')
            for container in email_containers:
                try:
                    text = container.text.strip()
                    if '@' in text:
                        email_parts = re.findall(r'\S+@\S+', text)
                        if email_parts:
                            email = email_parts[0]
                            logging.info(f"成功获取邮箱地址: {email}")
                            return email
                except Exception:
                    continue
            
            # 方式3: 直接从页面源码中提取
            page_source = driver.page_source
            email_matches = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', page_source)
            if email_matches:
                for potential_email in email_matches:
                    if len(potential_email) > 5:
                        logging.info(f"从页面源码中提取到邮箱地址: {potential_email}")
                        return potential_email
            
            logging.warning(f"尝试 {attempt+1}/{max_retries} 次后仍未获取到邮箱地址")
            time.sleep(3)
            
        except Exception as e:
            logging.error(f"获取临时邮箱时出错: {e}")
            time.sleep(3)
    
    logging.error("达到最大重试次数，无法获取临时邮箱")
    return None

# 获取验证码
def get_verification_code(driver):
    max_attempts = 5
    for attempt in range(max_attempts):
        logging.info(f"尝试获取验证码 (第 {attempt+1}/{max_attempts} 次)")
        time.sleep(5)  # 等待邮件到达
        
        try:
            # 刷新页面确保邮件显示
            driver.refresh()
            time.sleep(3)
            
            # 获取整个页面文本，尝试直接从页面中提取验证码
            page_source = driver.page_source
            
            # 尝试多种格式提取验证码
            patterns = [
                r'验证码：(\d{6})',
                r'DayDayMap验证码：(\d{6})',
                r'【盛邦安全】.*?：(\d{6})',
                r'(\d{6})',  # 兜底：任意6位数字
            ]
            
            for pattern in patterns:
                code_match = re.search(pattern, page_source)
                if code_match:
                    code = code_match.group(1)
                    # 确保是6位数字
                    if len(code) == 6 and code.isdigit():
                        logging.info(f"成功获取验证码: {code}")
                        return code
            
            # 尝试查找邮件列表元素并点击查看
            try:
                # 查找所有可能的邮件元素
                potential_emails = driver.find_elements(By.XPATH, "//div | //tr | //td | //span")
                for element in potential_emails:
                    text = element.text
                    if '验证码' in text or '盛邦安全' in text:
                        try:
                            element.click()
                            time.sleep(2)
                            # 再次尝试提取验证码
                            new_page_source = driver.page_source
                            for pattern in patterns:
                                code_match = re.search(pattern, new_page_source)
                                if code_match:
                                    code = code_match.group(1)
                                    if len(code) == 6 and code.isdigit():
                                        logging.info(f"点击邮件后成功获取验证码: {code}")
                                        return code
                        except:
                            pass
            except Exception as e:
                logging.warning(f"查找邮件元素时出错: {e}")
            
            logging.info(f"第 {attempt+1} 次尝试未找到验证码，继续等待...")
            
        except Exception as e:
            logging.error(f"获取验证码时出错: {e}")
    
    logging.error("达到最大尝试次数，无法获取验证码")
    return None

# 主注册函数
def register_account():
    # 初始化WebDriver
    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    # 添加网络连接相关配置
    options.add_argument('--disable-features=IsolateOrigins,site-per-process')
    
    driver = None
    try:
        # 使用WebDriverManager自动管理ChromeDriver
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.set_page_load_timeout(60)  # 设置页面加载超时时间
        driver.set_script_timeout(60)  # 设置脚本执行超时时间
        
        # 获取临时邮箱
        email = get_temp_email(driver)
        if not email:
            raise Exception("无法获取临时邮箱")
        
        logging.info(f"获取到临时邮箱: {email}")
        
        # 打开新标签页用于注册
        driver.execute_script("window.open('about:blank');")
        driver.switch_to.window(driver.window_handles[1])
        
        # 访问注册页面
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                driver.get('https://www.daydaymap.com/user/register')
                # 等待页面加载完成
                WebDriverWait(driver, 30).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
                logging.info(f"成功访问注册页面 (尝试 {attempt+1}/{max_attempts})")
                time.sleep(2)
                break
            except Exception as e:
                logging.error(f"无法访问注册页面 (尝试 {attempt+1}/{max_attempts}): {e}")
                if attempt < max_attempts - 1:
                    logging.info("等待后重试...")
                    time.sleep(3)
                else:
                    # 尝试使用备用方式
                    try:
                        logging.info("尝试备用方式访问...")
                        driver.get('about:blank')
                        driver.execute_script(f"window.location.href = 'https://www.daydaymap.com/user/register';")
                        time.sleep(5)
                    except Exception as backup_error:
                        logging.error(f"备用方式也失败: {backup_error}")
                        raise Exception(f"无法访问注册页面: {str(e)}")
        
        # 生成随机信息
        nickname = generate_chinese_name()
        password = generate_password()
        
        logging.info(f"生成的昵称: {nickname}")
        logging.info(f"生成的密码: {password}")
        
        # 填写注册表单
        try:
            # 填写邮箱 - 尝试多种方式
            email_input = None
            try:
                email_input = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.NAME, 'email'))
                )
            except:
                try:
                    email_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//input[@type='email']"))
                    )
                except:
                    email_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='email']"))
                    )
            
            email_input.clear()
            email_input.send_keys(email)
            logging.info("已填写邮箱")
            
            # 填写昵称
            nickname_input = None
            try:
                nickname_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, 'nickname'))
                )
            except:
                nickname_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@placeholder='昵称' or @placeholder='Nickname']"))
                )
            
            nickname_input.clear()
            nickname_input.send_keys(nickname)
            logging.info("已填写昵称")
            
            # 填写密码
            password_input = None
            try:
                password_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, 'password'))
                )
            except:
                password_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//input[@type='password'][1]"))
                )
            
            password_input.clear()
            password_input.send_keys(password)
            logging.info("已填写密码")
            
            # 确认密码
            confirm_password_input = None
            try:
                confirm_password_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.NAME, 'confirmPassword'))
                )
            except:
                try:
                    confirm_password_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.NAME, 'confirm_password'))
                    )
                except:
                    confirm_password_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//input[@type='password'][2]"))
                    )
            
            confirm_password_input.clear()
            confirm_password_input.send_keys(password)
            logging.info("已确认密码")
            
            # 点击获取验证码按钮
            send_code_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Send code') or contains(text(), '发送验证码') or contains(@class, 'code')]"))
            )
            send_code_button.click()
            logging.info("已点击发送验证码")
            
            # 切换回临时邮箱标签页获取验证码
            driver.switch_to.window(driver.window_handles[0])
            code = get_verification_code(driver)
            
            if code:
                logging.info(f"获取到验证码: {code}")
                
                # 切换回注册标签页填写验证码
                driver.switch_to.window(driver.window_handles[1])
                
                # 填写验证码
                code_input = None
                try:
                    code_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.NAME, 'code'))
                    )
                except:
                    code_input = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='验证码' or @placeholder='Verification Code']"))
                    )
                
                code_input.clear()
                code_input.send_keys(code)
                logging.info("已填写验证码")
                
                # 勾选同意协议
                try:
                    agreement_checkbox = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, '.agreement-checkbox, #agreement, [type="checkbox"]'))
                    )
                    if not agreement_checkbox.is_selected():
                        agreement_checkbox.click()
                    logging.info("已勾选同意协议")
                except Exception as e:
                    logging.warning(f"勾选同意协议失败: {e}")
                    # 尝试通过点击文本区域来勾选
                    try:
                        agreement_text = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '同意') or contains(text(), 'agree')]"))
                        )
                        agreement_text.click()
                        logging.info("已通过文本点击勾选同意协议")
                    except:
                        pass
                
                # 点击注册按钮
                register_button = WebDriverWait(driver, 15).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '注册') or contains(text(), 'Register') or @type='submit']"))
                )
                register_button.click()
                logging.info("已点击注册按钮")
                
                # 等待注册结果
                time.sleep(5)
                
                # 检查是否注册成功
                success = False
                try:
                    # 查找成功提示
                    success_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '成功') or contains(text(), 'Success') or contains(text(), 'welcome') or contains(text(), '欢迎')]")
                    if success_elements:
                        success = True
                    
                    # 检查URL变化
                    if 'success' in driver.current_url.lower() or 'login' in driver.current_url.lower():
                        success = True
                    
                    # 检查是否有错误提示
                    error_elements = driver.find_elements(By.XPATH, "//*[contains(text(), '错误') or contains(text(), 'error') or contains(text(), '失败')]")
                    if error_elements:
                        success = False
                        logging.warning(f"发现错误提示: {error_elements[0].text}")
                except Exception as e:
                    logging.error(f"检查注册结果时出错: {e}")
                
                result = {
                    'email': email,
                    'nickname': nickname,
                    'password': password,
                    'code': code,
                    'success': success
                }
                
                # 保存结果到文件
                save_result(result)
                
                if success:
                    logging.info("注册成功！")
                else:
                    logging.warning("注册失败，请检查可能的错误")
            else:
                logging.error("无法获取验证码")
                result = {
                    'email': email,
                    'nickname': nickname,
                    'password': password,
                    'code': None,
                    'success': False,
                    'error': '无法获取验证码'
                }
                save_result(result)
                
        except Exception as e:
            logging.error(f"填写表单时出错: {e}")
            result = {
                'email': email,
                'nickname': nickname,
                'password': password,
                'code': None,
                'success': False,
                'error': str(e)
            }
            save_result(result)
        
    except Exception as e:
        logging.error(f"注册过程出错: {e}")
        # 保存错误信息
        result = {
            'email': '未知',
            'nickname': '未知',
            'password': '未知',
            'code': None,
            'success': False,
            'error': f'注册过程出错: {str(e)}'
        }
        save_result(result)
    finally:
        # 关闭浏览器
        if driver:
            try:
                driver.quit()
                logging.info("浏览器已关闭")
            except:
                pass

# 保存结果到文件
def save_result(result):
    try:
        # 确保文件路径正确
        file_path = 'results.md'
        
        # 读取现有结果
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
        except FileNotFoundError:
            existing_content = "# 注册结果\n\n"
            existing_content += "| 邮箱 | 昵称 | 密码 | 验证码 | 注册状态 | 错误信息 |\n"
            existing_content += "|------|------|------|--------|----------|----------|\n"
        
        # 添加新结果
        status = "✅ 成功" if result['success'] else "❌ 失败"
        error_info = result.get('error', '-')
        
        new_line = f"| {result['email']} | {result['nickname']} | {result['password']} | {result.get('code', '-')} | {status} | {error_info} |\n"
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(existing_content + new_line)
        
        logging.info(f"结果已保存到 {file_path}")
    except Exception as e:
        logging.error(f"保存结果时出错: {e}")

# 执行注册
if __name__ == "__main__":
    logging.info("开始注册过程...")
    register_account()
    logging.info("注册过程完成。")
    
    # 显示结果文件路径
    try:
        import os
        result_file_path = os.path.abspath('results.md')
        logging.info(f"注册结果保存在: {result_file_path}")
    except:
        pass