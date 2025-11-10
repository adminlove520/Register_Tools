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
        time.sleep(8 if attempt == 0 else 5)  # 第一次等待更长时间
        
        try:
            # 刷新页面确保邮件显示
            driver.refresh()
            
            # 等待页面加载完成
            try:
                WebDriverWait(driver, 15).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
            except:
                pass  # 即使等待超时也继续执行
            
            time.sleep(2)
            
            # 获取整个页面文本，尝试直接从页面中提取验证码
            page_source = driver.page_source
            page_text = driver.find_element(By.TAG_NAME, 'body').text
            
            # 尝试多种格式提取验证码
            patterns = [
                r'验证码：(\d{6})',
                r'DayDayMap验证码：(\d{6})',
                r'【盛邦安全】.*?：(\d{6})',
                r'验证码是(\d{6})',
                r'验证码为(\d{6})',
                r'code：(\d{6})',
                r'code is (\d{6})',
                r'您的验证码是(\d{6})',
                r'为您的账号安全，您的验证码是：(\d{6})',
                r'(?<!\d)(\d{6})(?!\d)',  # 独立的6位数字，不与其他数字相连
            ]
            
            # 先从可见文本中提取
            logging.info("尝试从页面可见文本中提取验证码...")
            for pattern in patterns:
                code_match = re.search(pattern, page_text)
                if code_match:
                    code = code_match.group(1)
                    if len(code) == 6 and code.isdigit():
                        # 验证这不是日期或时间格式
                        if not (code.startswith('20') and len(code) == 6):
                            logging.info(f"从可见文本成功获取验证码: {code}")
                            return code
            
            # 再从页面源码中提取
            logging.info("尝试从页面源码中提取验证码...")
            for pattern in patterns:
                code_match = re.search(pattern, page_source)
                if code_match:
                    code = code_match.group(1)
                    if len(code) == 6 and code.isdigit():
                        if not (code.startswith('20') and len(code) == 6):
                            logging.info(f"从页面源码成功获取验证码: {code}")
                            return code
            
            # 尝试查找邮件列表元素并点击查看
            try:
                logging.info("尝试查找并点击邮件元素...")
                # 使用更精确的邮件元素定位
                email_selectors = [
                    "//div[contains(@class, 'mail-item')]",
                    "//tr[contains(@class, 'mail-row')]",
                    "//div[contains(text(), '验证码') or contains(text(), 'Verification')]",
                    "//a[contains(text(), '盛邦安全') or contains(text(), 'SafeDog')]",
                    "//div[contains(@class, 'email-content')]",
                    "//div[contains(@id, 'mail')]",
                ]
                
                found_mail = False
                for selector in email_selectors:
                    try:
                        potential_emails = driver.find_elements(By.XPATH, selector)
                        if potential_emails:
                            logging.info(f"通过选择器 '{selector}' 找到 {len(potential_emails)} 个邮件元素")
                            for element in potential_emails[:3]:  # 只检查前3个
                                try:
                                    text = element.text
                                    if text.strip():
                                        logging.info(f"检查邮件元素文本: {text[:50]}...")
                                        if '验证码' in text or '盛邦安全' in text or 'SafeDog' in text:
                                            # 滚动到元素可见
                                            driver.execute_script("arguments[0].scrollIntoView(true);", element)
                                            time.sleep(1)
                                            
                                            # 尝试点击
                                            try:
                                                element.click()
                                                logging.info("成功点击邮件元素")
                                            except:
                                                # 使用JavaScript点击
                                                driver.execute_script("arguments[0].click();", element)
                                                logging.info("通过JavaScript点击邮件元素")
                                            
                                            time.sleep(3)
                                            found_mail = True
                                            
                                            # 再次尝试提取验证码
                                            new_page_source = driver.page_source
                                            new_page_text = driver.find_element(By.TAG_NAME, 'body').text
                                            
                                            for pattern in patterns:
                                                # 先检查可见文本
                                                code_match = re.search(pattern, new_page_text)
                                                if code_match:
                                                    code = code_match.group(1)
                                                    if len(code) == 6 and code.isdigit():
                                                        logging.info(f"点击邮件后从可见文本获取验证码: {code}")
                                                        return code
                                                # 再检查源码
                                                code_match = re.search(pattern, new_page_source)
                                                if code_match:
                                                    code = code_match.group(1)
                                                    if len(code) == 6 and code.isdigit():
                                                        logging.info(f"点击邮件后从源码获取验证码: {code}")
                                                        return code
                                                
                                            # 如果点击后没找到，继续尝试下一个元素
                                except Exception as inner_e:
                                    logging.warning(f"处理邮件元素时出错: {inner_e}")
                        
                        if found_mail:
                            break
                    except Exception as sel_e:
                        logging.warning(f"使用选择器 '{selector}' 查找邮件时出错: {sel_e}")
                        
            except Exception as e:
                logging.warning(f"查找邮件元素时出错: {e}")
            
            # 最后尝试直接提取所有6位数字
            logging.info("尝试直接提取所有6位数字...")
            all_digits = re.findall(r'(?<!\d)(\d{6})(?!\d)', page_text)
            if all_digits:
                # 选择最有可能的验证码（通常是页面中唯一的6位数字或最后出现的）
                for code in reversed(all_digits):  # 从后往前检查
                    if len(code) == 6 and code.isdigit():
                        if not (code.startswith('20') and len(code) == 6):
                            logging.info(f"直接提取6位数字作为验证码: {code}")
                            return code
            
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
        import os
        file_path = os.path.join(os.getcwd(), 'results.md')
        
        # 清理和安全化数据
        def sanitize_value(value):
            if value is None:
                return "None"
            # 转换为字符串并处理可能的编码问题
            value_str = str(value)
            # 替换表格分隔符和换行符
            value_str = value_str.replace("|", "-")
            value_str = value_str.replace("\n", " ")
            # 限制长度
            if len(value_str) > 100:
                value_str = value_str[:97] + "..."
            return value_str
        
        # 准备安全的结果数据
        safe_result = {
            'email': sanitize_value(result.get('email', '未知')),
            'nickname': sanitize_value(result.get('nickname', '未知')),
            'password': sanitize_value(result.get('password', '未知')),
            'code': sanitize_value(result.get('code', '-')),
            'success': result.get('success', False),
            'error': sanitize_value(result.get('error', '-'))
        }
        
        # 读取现有结果
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
        except FileNotFoundError:
            # 使用更简单的表头，避免特殊字符
            existing_content = "# 注册结果\n\n"
            existing_content += "| 邮箱 | 昵称 | 密码 | 验证码 | 注册状态 | 错误信息 |\n"
            existing_content += "|------|------|------|--------|----------|----------|\n"
        except UnicodeDecodeError:
            # 如果编码错误，重新创建文件
            logging.warning("文件编码错误，重新创建结果文件")
            existing_content = "# 注册结果\n\n"
            existing_content += "| 邮箱 | 昵称 | 密码 | 验证码 | 注册状态 | 错误信息 |\n"
            existing_content += "|------|------|------|--------|----------|----------|\n"
        
        # 添加新结果，使用简单的状态表示
        status = "成功" if safe_result['success'] else "失败"
        
        # 构建新行，确保所有字段都被正确处理
        new_line = f"| {safe_result['email']} | {safe_result['nickname']} | {safe_result['password']} | {safe_result['code']} | {status} | {safe_result['error']} |\n"
        
        # 写入文件 - 尝试多种编码
        encoding_success = False
        encodings_to_try = ['utf-8', 'utf-8-sig', 'gbk', 'cp936']
        
        for encoding in encodings_to_try:
            try:
                with open(file_path, 'w', encoding=encoding) as f:
                    f.write(existing_content + new_line)
                logging.info(f"结果已使用{encoding}编码保存到 {file_path}")
                encoding_success = True
                break
            except Exception as enc_e:
                logging.warning(f"使用{encoding}编码保存失败: {enc_e}")
        
        # 如果所有编码都失败，使用二进制模式保存
        if not encoding_success:
            try:
                # 将字符串转换为字节，替换无法编码的字符
                content_bytes = (existing_content + new_line).encode('utf-8', errors='replace')
                with open(file_path, 'wb') as f:
                    f.write(content_bytes)
                logging.info(f"使用二进制模式成功保存结果到 {file_path}")
            except Exception as binary_e:
                logging.error(f"所有保存方式都失败: {binary_e}")
                # 最后尝试打印到控制台
                print("\n===== 无法保存到文件，结果如下 =====")
                print(f"邮箱: {safe_result['email']}")
                print(f"昵称: {safe_result['nickname']}")
                print(f"密码: {safe_result['password']}")
                print(f"验证码: {safe_result['code']}")
                print(f"注册状态: {status}")
                print(f"错误信息: {safe_result['error']}")
                print("=================================\n")
    
    except Exception as e:
        logging.error(f"保存结果时出错: {e}")
        # 紧急打印结果到控制台
        try:
            print("\n紧急结果输出:")
            for key, value in result.items():
                print(f"{key}: {value}")
        except:
            pass

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