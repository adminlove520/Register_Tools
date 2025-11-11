import time
import random
import re
import logging
import requests
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, ElementNotInteractableException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
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

# 生成随机中文昵称（符合4-16字符要求，看起来像正常用户）
def generate_chinese_name():
    # 常用中文名组合
    surnames = ['王', '李', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴', '徐', '孙', '胡', '朱', '高', '林', '何', '郭', '马', '罗']
    
    # 常用中文名字字符
    common_characters = [
        '明', '华', '强', '丽', '敏', '静', '磊', '军', '洋', '勇', 
        '艳', '杰', '娟', '涛', '辉', '梅', '超', '秀', '霞', '永', 
        '芳', '庆', '辉', '健', '英', '浩', '林', '丹', '宇', '宁',
        '梦', '雪', '欣', '佳', '雨', '思', '瑞', '阳', '轩', '子'
    ]
    
    # 选择一个姓氏
    surname = random.choice(surnames)
    
    # 选择2-15个常用字作为名字部分（使总长度在3-16之间）
    name_length = random.randint(2, 15)
    given_name = ''.join(random.choices(common_characters, k=name_length))
    
    # 组合成完整的中文名
    full_name = surname + given_name
    
    # 确保最终长度在4-16字符之间
    while len(full_name) < 4 or len(full_name) > 16:
        if len(full_name) < 4:
            full_name += random.choice(common_characters)
        else:
            full_name = full_name[:16]
    
    return full_name

# 生成符合要求的密码（8-30字符，必须包含大小写字母、数字和特殊字符）
def generate_password():
    # 定义字符集
    lower_chars = 'abcdefghijklmnopqrstuvwxyz'
    upper_chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    digit_chars = '0123456789'
    special_chars = '~!@#$%^'
    
    # 选择密码长度（8-30）
    length = random.randint(10, 20)  # 选择一个合理的长度范围
    
    # 确保包含每种类型的字符
    password = [
        random.choice(lower_chars),
        random.choice(upper_chars),
        random.choice(digit_chars),
        random.choice(special_chars)
    ]
    
    # 剩余位置随机填充所有类型的字符
    all_chars = lower_chars + upper_chars + digit_chars + special_chars
    password.extend(random.choices(all_chars, k=length-4))
    
    # 打乱密码字符顺序
    random.shuffle(password)
    
    # 组合成最终密码
    return ''.join(password)

def test_network_connection(url, timeout=10):
    """测试网络连接"""
    logging.info(f"测试网络连接: {url}")
    try:
        # 不验证SSL证书，添加User-Agent
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, timeout=timeout, verify=False, headers=headers)
        logging.info(f"连接测试成功: {url}, 状态码: {response.status_code}")
        return True, response.status_code
    except requests.exceptions.ConnectionError as e:
        logging.error(f"连接错误: {url}, 错误: {str(e)}")
        return False, f"连接错误: {str(e)}"
    except requests.exceptions.Timeout as e:
        logging.error(f"连接超时: {url}, 错误: {str(e)}")
        return False, f"超时错误: {str(e)}"
    except Exception as e:
        logging.error(f"网络测试异常: {url}, 错误: {str(e)}")
        return False, f"异常: {str(e)}"

# 获取临时邮箱
def get_temp_email(driver):
    # 先测试网络连接
    email_site = 'http://mail0.dfyx.xyz/'
    connected, status = test_network_connection(email_site)
    if not connected:
        logging.error(f"无法连接到临时邮箱网站: {status}")
        return None
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 打开临时邮箱网站
            logging.info(f"尝试访问临时邮箱网站 (尝试 {attempt+1}/{max_retries})\n")
            driver.set_page_load_timeout(30)
            driver.get(email_site)
            
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

# 处理滑动验证
def handle_slider_verification(driver):
    """
    增强版滑动验证处理，支持更多滑动验证类型和更智能的拖动策略
    """
    logging.info("开始处理滑动验证...")
    
    # 增强的滑块定位策略列表
    slider_locators = [
        # puzzle-captcha 特定定位器 (根据用户提供的HTML结构)
        (By.CSS_SELECTOR, '.puzzle-captcha .slider'),
        (By.CSS_SELECTOR, '.slider-wrap .slider'),
        (By.XPATH, "//div[contains(@class, 'puzzle-captcha')]//div[@class='slider']"),
        (By.XPATH, "//div[contains(@class, 'slider-wrap')]//div[@class='slider']"),
        
        # 常见滑动验证类名
        (By.CSS_SELECTOR, '.slider'),
        (By.CSS_SELECTOR, '.geetest_slider_button'),
        (By.CSS_SELECTOR, '.captcha-slider'),
        (By.CSS_SELECTOR, '.slider-btn'),
        (By.CSS_SELECTOR, '.drag-handle'),
        (By.CSS_SELECTOR, '.nc_iconfont.btn_slide'),
        (By.CSS_SELECTOR, '.tcaptcha-drag-button'),
        
        # XPath模糊匹配
        (By.XPATH, "//div[contains(@class, 'slider')]"),
        (By.XPATH, "//div[contains(@class, 'drag')]"),
        (By.XPATH, "//div[contains(@class, 'move')]"),
        (By.XPATH, "//button[contains(@class, 'slider')]"),
        (By.XPATH, "//span[contains(@class, 'slider')]"),
        
        # 特殊属性匹配
        (By.XPATH, "//*[@draggable='true']"),
        (By.XPATH, "//*[contains(text(), '拖动')]"),
        (By.XPATH, "//*[contains(text(), '滑动')]")
    ]
    
    slider = None
    found_in_iframe = False
    
    # 1. 先在主页面查找滑块
    for locator_type, locator_value in slider_locators:
        try:
            slider = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((locator_type, locator_value)))
            logging.info(f"找到滑动验证元素: {locator_type}={locator_value}")
            break
        except Exception:
            continue
    
    # 2. 如果主页面没找到，尝试在所有iframe中查找
    if not slider:
        try:
            iframes = driver.find_elements(By.TAG_NAME, 'iframe')
            logging.info(f"找到{len(iframes)}个iframe，开始在其中查找滑块...")
            
            for i, iframe in enumerate(iframes):
                try:
                    driver.switch_to.frame(iframe)
                    logging.info(f"在iframe[{i}]中查找滑块...")
                    
                    # 在iframe中尝试所有定位策略
                    for locator_type, locator_value in slider_locators:
                        try:
                            slider = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((locator_type, locator_value)))
                            logging.info(f"在iframe[{i}]中找到滑动验证: {locator_type}={locator_value}")
                            found_in_iframe = True
                            break
                        except Exception:
                            continue
                    
                    if slider:
                        break
                    
                    driver.switch_to.default_content()
                except Exception as e:
                    logging.warning(f"切换到iframe[{i}]时出错: {e}")
                    driver.switch_to.default_content()
                    continue
        except Exception as e:
            logging.warning(f"查找iframe时出错: {e}")
    
    if slider:
        try:
            # 等待滑块完全加载
            WebDriverWait(driver, 2).until(lambda d: slider.is_displayed() and slider.is_enabled())
            
            # 滚动到滑块可见
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", slider)
            time.sleep(random.uniform(0.5, 1.0))
            
            # 创建ActionChains
            actions = ActionChains(driver)
            
            # 获取滑块位置和尺寸
            slider_location = slider.location
            slider_size = slider.size
            logging.info(f"滑块位置: {slider_location}, 尺寸: {slider_size}")
            
            # 尝试多种方式确定拖动距离
            drag_distance = None
            
            # 方式1: 针对puzzle-captcha类型的特定计算
            try:
                # 检查是否是puzzle-captcha类型
                puzzle_container = driver.find_element(By.CSS_SELECTOR, '.puzzle-captcha')
                if puzzle_container:
                    logging.info("检测到puzzle-captcha类型的验证码")
                    
                    # 查找gap canvas元素
                    gap_canvas = driver.find_element(By.CSS_SELECTOR, '.gap')
                    bg_canvas = driver.find_element(By.CSS_SELECTOR, '.bg')
                    
                    # 获取canvas尺寸作为参考
                    gap_size = gap_canvas.size
                    bg_size = bg_canvas.size
                    logging.info(f"puzzle-captcha尺寸 - 背景: {bg_size}, 缺口: {gap_size}")
                    
                    # 根据puzzle-captcha特点估算拖动距离
                    # 通常拖动距离在100-250px之间，根据背景图宽度调整
                    if bg_size['width'] > 300:
                        drag_distance = random.randint(150, 250)
                    else:
                        drag_distance = random.randint(100, 200)
                    logging.info(f"为puzzle-captcha类型设置拖动距离: {drag_distance}px")
            except Exception:
                pass
            
            # 方式2: 通过背景图片缺口位置计算（针对常见的缺口验证）
            try:
                # 查找滑块背景或容器元素
                containers = driver.find_elements(By.XPATH, "//div[contains(@class, 'slider') or contains(@class, 'captcha')]")
                for container in containers:
                    style = container.get_attribute('style')
                    if 'background-image' in style:
                        # 这里可以添加更复杂的图像分析逻辑，暂时使用估算值
                        logging.info("发现背景图像，使用估算拖动距离")
                        drag_distance = random.randint(200, 300)
                        break
            except Exception:
                pass
            
            # 方式2: 通过轨道元素计算
            if drag_distance is None:
                try:
                    track_locators = [
                        (By.CSS_SELECTOR, '.slider-track'),
                        (By.CSS_SELECTOR, '.slider-container'),
                        (By.CSS_SELECTOR, '.captcha-container'),
                        (By.XPATH, "//div[contains(@class, 'track')]")
                    ]
                    
                    for locator_type, locator_value in track_locators:
                        try:
                            track = driver.find_element(locator_type, locator_value)
                            track_size = track.size
                            drag_distance = track_size['width'] - slider_size['width']
                            logging.info(f"通过轨道计算拖动距离: {drag_distance}px")
                            break
                        except Exception:
                            continue
                except Exception:
                    pass
            
            # 方式3: 使用默认值
            if drag_distance is None:
                drag_distance = random.randint(200, 300)
                logging.info(f"使用默认拖动距离: {drag_distance}px")
            
            # 智能人类拖动路径生成算法
            def generate_human_path(target_distance):
                """生成更接近人类操作的拖动路径"""
                path = []
                current_distance = 0
                
                # 1. 初始加速阶段
                acceleration_distance = int(target_distance * random.uniform(0.3, 0.5))
                for i in range(5):
                    step = int(acceleration_distance / 5 * (1 + random.uniform(0.1, 0.3)))
                    current_distance += step
                    path.append((step, random.randint(-3, 3) * 0.5))
                    if current_distance >= target_distance:
                        break
                
                # 2. 匀速阶段
                if current_distance < target_distance:
                    uniform_distance = int((target_distance - current_distance) * random.uniform(0.4, 0.6))
                    for i in range(random.randint(3, 5)):
                        step = int(uniform_distance / random.randint(3, 5))
                        current_distance += step
                        path.append((step, random.randint(-2, 2) * 0.3))
                        if current_distance >= target_distance:
                            break
                
                # 3. 减速阶段
                if current_distance < target_distance:
                    remaining = target_distance - current_distance
                    deceleration_steps = random.randint(3, 5)
                    for i in range(deceleration_steps):
                        factor = 1 - (i / deceleration_steps)
                        step = int(remaining * factor * random.uniform(0.8, 1.2) / deceleration_steps)
                        current_distance += step
                        path.append((step, random.randint(-3, 3) * 0.4))
                        if current_distance >= target_distance:
                            break
                
                # 4. 微调修正
                if current_distance < target_distance:
                    path.append((target_distance - current_distance, 0))
                
                return path
            
            # 执行滑动操作
            try:
                # 鼠标移动到滑块，稍微停顿，模拟人类准备操作
                actions.move_to_element(slider).perform()
                time.sleep(random.uniform(0.2, 0.5))
                
                # 点击并按住
                actions.click_and_hold(slider).perform()
                logging.info("开始拖动滑块")
                time.sleep(random.uniform(0.1, 0.3))  # 按住后短暂停顿
                
                # 生成并执行人类路径
                human_path = generate_human_path(drag_distance)
                for step_x, step_y in human_path:
                    actions.move_by_offset(step_x, step_y).perform()
                    time.sleep(random.uniform(0.01, 0.05))
                
                # 释放前稍微停顿，模拟确认位置
                time.sleep(random.uniform(0.1, 0.3))
                actions.release().perform()
                logging.info("完成滑块拖动")
                
                # 等待验证完成
                time.sleep(random.uniform(1.5, 2.5))
                
                # 检查是否验证成功（针对puzzle-captcha类型的特定检查）
                try:
                    # 检查提示信息
                    success_tip = driver.find_element(By.CSS_SELECTOR, '.result-tip:not(.fail-tip)')
                    if success_tip and success_tip.is_displayed():
                        logging.info(f"puzzle-captcha验证成功: {success_tip.text}")
                        return True
                    
                    # 检查滑块容器是否仍然可见（隐藏表示验证成功）
                    puzzle_container = driver.find_element(By.CSS_SELECTOR, '.puzzle-captcha')
                    if not puzzle_container.is_displayed():
                        logging.info("puzzle-captcha验证成功，容器已隐藏")
                        return True
                except Exception:
                    pass
                
                return True
            except Exception as e:
                logging.error(f"执行拖动时出错: {e}")
                
                # 尝试JavaScript方式拖动
                try:
                    logging.info("尝试使用JavaScript拖动")
                    driver.execute_script("""
                        const slider = arguments[0];
                        const distance = arguments[1];
                        
                        // 创建鼠标事件
                        function createMouseEvent(type) {
                            const event = new MouseEvent(type, {
                                bubbles: true,
                                cancelable: true,
                                view: window
                            });
                            return event;
                        }
                        
                        // 点击并按住
                        slider.dispatchEvent(createMouseEvent('mousedown'));
                        
                        // 模拟拖动
                        const steps = Math.floor(distance / 10);
                        for (let i = 0; i <= steps; i++) {
                            const offsetX = (i / steps) * distance;
                            const event = new MouseEvent('mousemove', {
                                bubbles: true,
                                cancelable: true,
                                view: window,
                                clientX: slider.getBoundingClientRect().left + offsetX,
                                clientY: slider.getBoundingClientRect().top + 10
                            });
                            slider.dispatchEvent(event);
                        }
                        
                        // 释放
                        setTimeout(() => {
                            slider.dispatchEvent(createMouseEvent('mouseup'));
                        }, 200);
                    """, slider, drag_distance)
                    time.sleep(2)
                    return True
                except Exception as js_error:
                    logging.error(f"JavaScript拖动失败: {js_error}")
            
        except Exception as e:
            logging.error(f"处理滑动验证时出错: {e}")
        finally:
            # 确保切回主页面
            try:
                if found_in_iframe:
                    driver.switch_to.default_content()
                    logging.info("已切回主页面")
            except Exception:
                pass
    
    logging.info("未找到或无法处理滑动验证，继续后续流程")
    return False

# 辅助函数：检查验证码发送成功提示
def check_success_message(driver):
    """检查是否有验证码发送成功的提示"""
    logging.info("检查验证码发送成功提示...")
    success_patterns = [
        "已发送", "sent", "success", "成功", "verification code sent", 
        "验证码已发送", "code has been sent", "发送成功", "验证码发送成功"
    ]
    
    # 尝试多种方式查找成功提示
    # 1. 通过文本内容查找
    try:
        for pattern in success_patterns:
            success_elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{pattern}')]")
            for elem in success_elements:
                if elem.is_displayed() and elem.size['width'] > 0 and elem.size['height'] > 0:
                    logging.info(f"检测到验证码发送成功提示: {elem.text}")
                    return True
    except Exception as e:
        logging.warning(f"检查成功提示失败: {e}")
    
    # 2. 检查是否有倒计时元素出现（通常验证码发送后会有倒计时）
    try:
        countdown_elements = driver.find_elements(By.XPATH, 
            "//*[contains(text(), '秒') or contains(text(), 's') or contains(@class, 'countdown') or contains(@id, 'countdown')]"
        )
        for elem in countdown_elements:
            if elem.is_displayed() and any(char.isdigit() for char in elem.text):
                logging.info(f"检测到验证码发送后的倒计时: {elem.text}")
                return True
    except Exception as e:
        logging.warning(f"检查倒计时元素失败: {e}")
    
    return False

# 智能验证码发送函数
def trigger_verification_code(driver):
    """
    智能触发验证码发送，尝试多种策略确保验证码能够发送
    
    Args:
        driver: WebDriver实例
    
    Returns:
        bool: 是否成功触发验证码发送
    """
    logging.info("开始尝试触发验证码发送...")
    
    # 验证码输入框定位策略 - 增强版
    verification_input_locators = [
        # 针对用户提供的HTML结构的特定定位器
        (By.XPATH, "//div[contains(@class, 'ant-formily-item')]//input[contains(@placeholder, '请输入验证码')]"),
        (By.XPATH, "//div[contains(@class, 'ant-formily-item')]//input[contains(@class, 'ant-input')]"),
        (By.XPATH, "//div[contains(@class, 'ant-input-affix-wrapper')]//input"),
        (By.XPATH, "//input[contains(@class, 'ant-input') and contains(@placeholder, '请输入验证码')]"),
        (By.XPATH, "//input[contains(@class, 'ant-input-lg')]"),
        
        # 原有定位策略
        (By.XPATH, "//input[@placeholder='Please enter the verification code']"),
        (By.XPATH, "//input[contains(@placeholder, 'verification')]"),
        (By.XPATH, "//input[contains(@placeholder, '验证码')]"),
        (By.XPATH, "//input[@type='text' and contains(@class, 'verification')]"),
        (By.XPATH, "//input[@id='verification-code']"),
        (By.XPATH, "//input[contains(@id, 'code')]"),
        # 新增定位策略
        (By.XPATH, "//input[@name='verification_code']"),
        (By.XPATH, "//input[@name='code']"),
        (By.XPATH, "//input[contains(@class, 'code') and @type='text']"),
        (By.XPATH, "//div[contains(text(), '验证码')]/following-sibling::input"),
        (By.XPATH, "//label[contains(text(), 'Verification')]/following-sibling::input")
    ]
    
    verification_input = None
    
    # 尝试定位验证码输入框 - 使用wait_for_element
    for locator_type, locator_value in verification_input_locators:
        try:
            verification_input = wait_for_element(driver, locator_type, locator_value, timeout=8, description="验证码输入框")
            if verification_input:
                # 额外确保元素可交互
                try:
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((locator_type, locator_value)))
                    logging.info(f"验证码输入框可交互: {locator_type}={locator_value}")
                    break
                except:
                    logging.warning(f"验证码输入框存在但不可交互")
                    continue
        except Exception as e:
            logging.warning(f"使用定位器 {locator_type}={locator_value} 未找到验证码输入框: {e}")
    
    if not verification_input:
        logging.error("无法定位验证码输入框，尝试其他方法...")
        
        # 尝试更广泛的定位策略
        try:
            verification_input = wait_for_element(driver, By.XPATH, "//input[@type='text']", timeout=5, description="文本输入框")
            if verification_input:
                logging.info("找到文本输入框，尝试将其作为验证码输入框")
        except:
            pass
    
    if not verification_input:
        logging.error("无法定位验证码输入框")
        return False
    
    # 保存当前窗口句柄，以便后续可能的操作
    current_window = driver.current_window_handle
    
    # 综合触发策略
    strategies = []
    
    # 策略1: 查找父元素内的可点击元素
    try:
        parent_element = verification_input.find_element(By.XPATH, '..')
        nearby_elements = parent_element.find_elements(By.XPATH, './/*')
        logging.info(f"在验证码输入框父元素中找到 {len(nearby_elements)} 个元素")
        
        # 诊断并添加可能的触发元素
        for i, elem in enumerate(nearby_elements[:15]):  # 限制数量避免过多尝试
            try:
                if elem.is_displayed() and elem.is_enabled() and elem != verification_input:
                    elem_text = elem.text.strip()
                    elem_tag = elem.tag_name
                    elem_class = elem.get_attribute('class')
                    elem_id = elem.get_attribute('id')
                    
                    # 判断是否可能是发送按钮
                    if (elem_tag in ['button', 'a', 'input'] or 
                        'code' in (elem_class or '').lower() or 
                        'send' in (elem_class or '').lower() or
                        '获取' in elem_text or 'send' in elem_text.lower() or 'code' in elem_text.lower()):
                        strategies.append((elem, f"父元素内元素 {i+1}: 标签={elem_tag}, 文本='{elem_text}'"))
            except Exception:
                pass
    except Exception as e:
        logging.warning(f"获取父元素信息失败: {e}")
    
    # 策略2: 查找所有包含code/send相关文本或类名的元素
    try:
        # 增强的XPATH表达式，包含针对ant-formily-item和ant-typography的检查
        code_elements = driver.find_elements(By.XPATH, 
            "//*[(contains(text(), 'code') or contains(text(), 'Code') or contains(text(), '验证码') or "
            "contains(text(), '获取验证码') or contains(text(), '获取') or contains(text(), 'send') or contains(text(), 'Send') or "
            "contains(@class, 'code') or contains(@id, 'code') or contains(@class, 'send') or "
            "contains(@id, 'send') or contains(@class, 'ant-typography') or "
            "contains(@class, 'ant-formily-item')) and not contains(@placeholder, 'verification')]"
        )
        
        for elem in code_elements[:10]:  # 限制数量
            try:
                if elem.is_displayed() and elem.is_enabled() and elem != verification_input:
                    elem_text = elem.text.strip()
                    elem_tag = elem.tag_name
                    strategies.append((elem, f"全局code元素: 标签={elem_tag}, 文本='{elem_text}'"))
            except Exception:
                pass
    except Exception as e:
        logging.warning(f"查找全局code元素失败: {e}")
    
    # 策略3: 尝试JavaScript查找和点击
    strategies.append((None, "JavaScript查找策略"))
    
    # 策略4: 点击验证码输入框后重新输入邮箱（模拟用户操作）
    strategies.append((None, "重新输入邮箱策略"))
    
    # 执行所有策略
    success = False
    for elem, strategy_name in strategies:
        try:
            logging.info(f"尝试策略: {strategy_name}")
            
            if elem:
                # 对找到的元素执行点击
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", elem)
                time.sleep(0.5)
                
                # 尝试多种点击方式
                try:
                    elem.click()
                    logging.info(f"成功点击元素: {strategy_name}")
                except:
                    try:
                        driver.execute_script("arguments[0].click();", elem)
                        logging.info(f"通过JavaScript成功点击元素: {strategy_name}")
                    except:
                        try:
                            actions = ActionChains(driver)
                            actions.move_to_element(elem).click().perform()
                            logging.info(f"通过ActionChains成功点击元素: {strategy_name}")
                        except:
                            logging.warning(f"所有点击方式都失败: {strategy_name}")
                            continue
                
                time.sleep(1.5)  # 等待可能的反馈
                
                # 检查是否有成功提示 - 使用辅助函数
                if check_success_message(driver):
                    success = True
                    break
                
                if success:
                    break
                
            elif strategy_name == "JavaScript查找策略":
                # JavaScript查找和触发策略
                logging.info("执行JavaScript查找验证码发送按钮")
                
                # 执行复杂的JavaScript查找逻辑
                send_button = driver.execute_script("""
                    // 查找可能的发送按钮
                    function findSendButton() {
                        // 查找包含特定文本的元素
                        const texts = ['发送验证码', 'Send Code', '获取验证码', 'Get Code', 'send', '获取'];
                        for (const text of texts) {
                            const elements = document.querySelectorAll('*');
                            for (const element of elements) {
                                if (element.textContent && element.textContent.includes(text) && 
                                    element.nodeName.match(/^(BUTTON|A|INPUT|SPAN|DIV)$/) &&
                                    element.offsetParent !== null) {
                                    return element;
                                }
                            }
                        }
                        
                        // 查找特定类名的元素
                        const classes = ['send-code', 'get-code', 'code-btn', 'verify-btn'];
                        for (const cls of classes) {
                            const element = document.querySelector(`.${cls}`);
                            if (element && element.offsetParent !== null) {
                                return element;
                            }
                        }
                        
                        // 查找针对用户提供的HTML结构的特定元素
                        // 1. 查找ant-input-suffix中的获取验证码链接
                        const suffixLink = document.querySelector('.ant-input-suffix .ant-typography:contains("获取验证码")');
                        if (suffixLink && suffixLink.offsetParent !== null) {
                            return suffixLink;
                        }
                        
                        // 2. 查找在ant-formily-item中的获取验证码元素
                        const formItemLink = document.querySelector('.ant-formily-item .ant-typography:contains("获取验证码")');
                        if (formItemLink && formItemLink.offsetParent !== null) {
                            return formItemLink;
                        }
                        
                        // 3. 查找带特定类的获取验证码元素
                        const typographyElement = document.querySelector('.ant-typography.ant-typography-disabled:contains("获取验证码")');
                        if (typographyElement && typographyElement.offsetParent !== null) {
                            return typographyElement;
                        }
                        
                        // 4. 查找ant-input-affix-wrapper中的suffix部分
                        const affixWrapper = document.querySelector('.ant-input-affix-wrapper');
                        if (affixWrapper) {
                            const suffix = affixWrapper.querySelector('.ant-input-suffix');
                            if (suffix) {
                                const textElements = suffix.querySelectorAll('*');
                                for (const el of textElements) {
                                    if (el.textContent && el.textContent.includes('获取验证码') && 
                                        ['A', 'SPAN', 'DIV'].includes(el.tagName)) {
                                        return el;
                                    }
                                }
                            }
                        }
                        
                        // 查找验证码输入框旁边的元素
                        const codeInputs = document.querySelectorAll('input[placeholder*="verification"], input[placeholder*="验证码"], input[id*="code"], input[name*="code"]');
                        for (const input of codeInputs) {
                            const nextSiblings = [];
                            let sibling = input.nextElementSibling;
                            while (sibling && nextSiblings.length < 3) {
                                nextSiblings.push(sibling);
                                sibling = sibling.nextElementSibling;
                            }
                            
                            for (const nextSibling of nextSiblings) {
                                if (nextSibling.nodeName.match(/^(BUTTON|A|INPUT|SPAN|DIV)$/) && nextSibling.offsetParent !== null) {
                                    return nextSibling;
                                }
                            }
                        }
                        
                        return null;
                    }
                    
                    const button = findSendButton();
                    if (button) {
                        // 确保元素可见并点击
                        button.scrollIntoView({behavior: 'smooth', block: 'center'});
                        setTimeout(() => {
                            button.click();
                        }, 500);
                        return button;
                    }
                    return null;
                """)
                
                if send_button:
                    logging.info("JavaScript成功找到并点击了发送按钮")
                    time.sleep(2)  # 等待响应
                    
                    # 检查成功提示 - 使用辅助函数
                    if check_success_message(driver):
                        success = True
                        break
                    
                    if success:
                        break
                
            elif strategy_name == "重新输入邮箱策略":
                # 点击验证码输入框
                driver.execute_script("arguments[0].focus();", verification_input)
                time.sleep(0.5)
                
                # 尝试重新输入邮箱（模拟用户操作流程）
                try:
                    email_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Please enter phone number or email address']")))
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", email_input)
                    time.sleep(0.5)
                    email_input.click()
                    email_input.send_keys(Keys.CONTROL + 'a')
                    email_input.send_keys(Keys.BACKSPACE)
                    time.sleep(0.5)
                    
                    # 重新输入邮箱
                    current_email = email_input.get_attribute('value')
                    if current_email:
                        email_input.send_keys(current_email)
                        logging.info("重新输入了邮箱地址")
                        
                        # 点击其他区域，可能触发表单验证和发送按钮激活
                        driver.execute_script("document.body.click();")
                        time.sleep(1)
                except Exception as e:
                    logging.warning(f"重新输入邮箱策略失败: {e}")
                
                # 检查是否有发送按钮被激活
                try:
                    active_buttons = driver.find_elements(By.XPATH, "//button[not(@disabled) or @disabled='false']")
                    for button in active_buttons:
                        try:
                            if button.is_displayed() and ('send' in button.text.lower() or 'code' in button.text.lower() or '获取' in button.text or '发送' in button.text):
                                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                                time.sleep(0.5)
                                driver.execute_script("arguments[0].click();", button)
                                logging.info(f"点击了激活的发送按钮: {button.text}")
                                time.sleep(1.5)
                                
                                # 检查成功提示 - 使用辅助函数
                                if check_success_message(driver):
                                    success = True
                                    break
                                
                                if success:
                                    break
                        except Exception:
                            pass
                except Exception:
                    pass
                
                if success:
                    break
                    
        except Exception as e:
            logging.error(f"执行策略 {strategy_name} 时出错: {e}")
            continue
    
    # 最后，尝试处理可能出现的滑动验证
    if not success:
        logging.info("尝试处理可能的滑动验证")
        handle_slider_verification(driver)
        
        # 再次尝试查找并点击发送按钮
        try:
            send_buttons = driver.find_elements(By.XPATH, 
                "//*[(contains(text(), 'send') or contains(text(), '获取') or contains(text(), '发送') or contains(text(), 'code')) and not contains(@placeholder, 'verification')]"
            )
            
            for button in send_buttons[:5]:
                try:
                    if button.is_displayed() and button.is_enabled():
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", button)
                        logging.info(f"滑动验证后再次点击发送按钮: {button.text}")
                        time.sleep(1.5)
                        
                        # 检查成功提示 - 使用辅助函数
                        if check_success_message(driver):
                            success = True
                            break
                        
                        if success:
                            break
                except Exception:
                    pass
        except Exception:
            pass
    
    # 确保切换回原始窗口
    try:
        if driver.current_window_handle != current_window:
            driver.switch_to.window(current_window)
    except Exception:
        pass
    
    logging.info(f"验证码发送触发{'成功' if success else '失败'}")
    return success

# 获取验证码
def get_verification_code(driver):
    max_attempts = 5
    email_site = 'http://mail0.dfyx.xyz/'
    
    # 确保访问正确的邮箱网站
    try:
        current_url = driver.current_url
        if email_site not in current_url:
            logging.info(f"导航到邮箱网站: {email_site}")
            driver.get(email_site)
            time.sleep(2)
    except Exception as e:
        logging.error(f"导航到邮箱网站时出错: {e}")
        driver.get(email_site)
        time.sleep(2)
    
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
                logging.info("尝试查找并点击包含'盛邦安全'的邮件...")
                # 优先查找包含'盛邦安全'的邮件
                logging.info("优先查找包含'盛邦安全'的邮件元素")
                
                # 先尝试点击刷新按钮确保新邮件显示
                try:
                    refresh_button = driver.find_element(By.XPATH, "//button[contains(@id, 'refresh') or contains(@class, 'refresh') or contains(text(), '刷新')]")
                    refresh_button.click()
                    logging.info("成功点击刷新按钮")
                    time.sleep(2)
                except Exception as e:
                    logging.warning(f"点击刷新按钮失败: {e}")
                
                # 优先查找包含'盛邦安全'的邮件元素
                safe_email_elements = driver.find_elements(By.XPATH, "//div[contains(text(), '盛邦安全')] | //span[contains(text(), '盛邦安全')] | //a[contains(text(), '盛邦安全')]")
                if safe_email_elements:
                    logging.info(f"找到 {len(safe_email_elements)} 个包含'盛邦安全'的元素")
                    for element in safe_email_elements:
                        try:
                            # 滚动到元素
                            driver.execute_script("arguments[0].scrollIntoView(true);", element)
                            time.sleep(1)
                            # 点击元素
                            element.click()
                            logging.info("成功点击包含'盛邦安全'的邮件元素")
                            time.sleep(2)
                            # 重新获取页面文本检查验证码
                            page_text = driver.find_element(By.TAG_NAME, 'body').text
                            page_source = driver.page_source
                            
                            # 再次尝试提取验证码
                            for pattern in patterns:
                                code_match = re.search(pattern, page_text) or re.search(pattern, page_source)
                                if code_match:
                                    code = code_match.group(1)
                                    if len(code) == 6 and code.isdigit() and not (code.startswith('20') and len(code) == 6):
                                        logging.info(f"点击邮件后成功获取验证码: {code}")
                                        return code
                        except Exception as e:
                            logging.warning(f"点击邮件元素时出错: {e}")
                
                # 如果没有找到特定邮件，尝试通用邮件选择器
                logging.info("尝试使用通用邮件选择器")
                email_selectors = [
                    "//div[contains(@class, 'mail-item')]",
                    "//tr[contains(@class, 'mail-row')]",
                    "//div[contains(text(), '验证码') or contains(text(), 'Verification')]",
                    "//a[contains(text(), 'SafeDog')]",
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
def find_chrome_driver():
    """增强版ChromeDriver查找，支持自动下载和版本管理"""
    # 常见的ChromeDriver位置
    common_paths = [
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google', 'Chrome', 'Application', 'chromedriver.exe'),
        os.path.join(os.environ.get('ProgramFiles', ''), 'Google', 'Chrome', 'Application', 'chromedriver.exe'),
        os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'Google', 'Chrome', 'Application', 'chromedriver.exe'),
        os.path.join(os.getcwd(), 'chromedriver.exe'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chromedriver.exe')
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            logging.info(f"找到ChromeDriver: {path}")
            return path
    
    # 检查PATH环境变量
    for path in os.environ['PATH'].split(os.pathsep):
        driver_path = os.path.join(path, 'chromedriver.exe')
        if os.path.exists(driver_path):
            logging.info(f"在PATH中找到ChromeDriver: {driver_path}")
            return driver_path
    
    logging.warning("未找到ChromeDriver，尝试使用webdriver_manager自动下载...")
    try:
        # 尝试使用webdriver_manager自动管理ChromeDriver
        logging.info("使用webdriver_manager获取ChromeDriver...")
        return ChromeDriverManager().install()
    except Exception as e:
        logging.error(f"webdriver_manager下载失败: {e}")
        logging.warning("请手动下载ChromeDriver并放在系统PATH或当前目录。")
        return None

def register_account():
    # 尝试查找ChromeDriver
    chrome_driver_path = find_chrome_driver()
    
    # 初始化WebDriver
    options = webdriver.ChromeOptions()
    
    # 基本配置
    options.add_argument('--start-maximized')
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--disable-popup-blocking')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # 关键网络配置 - 解决连接问题
    options.add_argument('--disable-features=IsolateOrigins,site-per-process')
    options.add_argument('--remote-allow-origins=*')
    options.add_argument('--disable-web-security')
    options.add_argument('--allow-running-insecure-content')
    options.add_argument('--disable-features=BlockInsecurePrivateNetworkRequests')
    
    # 明确禁用代理设置
    options.add_argument('--no-proxy-server')
    options.add_argument('--proxy-bypass-list=*')
    options.add_argument('--disable-auto-reload')
    
    # 禁用代理自动检测
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    # 设置无代理环境变量
    options.add_argument('--disable-features=NetworkService,NetworkServiceInProcess')
    
    # 禁用连接限制
    options.add_argument('--disable-features=CrossSiteDocumentBlockingIfIsolating')
    options.add_argument('--disable-features=site-per-process')
    
    # 页面加载策略
    options.page_load_strategy = 'eager'  # 更快的页面加载策略
    
    # 禁用某些安全功能可能会有所帮助
    options.add_argument('--disable-features=site-per-process')
    options.add_argument('--disable-features=IsolateOrigins')
    
    # 设置用户配置文件以避免某些Chrome策略限制
    options.add_argument('--profile-directory=Default')
    options.add_argument('--disable-features=TranslateUI')
    
    # 添加实验性选项以解决可能的网络问题
    prefs = {
        'download.prompt_for_download': False,
        'download.directory_upgrade': True,
        'safebrowsing.enabled': False,
        'safebrowsing.disable_download_protection': True,
        # 禁用代理自动检测
        'system.network.proxy.autodetect': False,
        'system.network.proxy.http_proxy': '',
        'system.network.proxy.ssl_proxy': ''
    }
    options.add_experimental_option('prefs', prefs)
    
    driver = None
    try:
        # 首先测试两个关键网站的可访问性
        email_site = 'http://mail0.dfyx.xyz/'
        register_site = 'https://www.daydaymap.com/user/register'
        
        logging.info("\n===== 网站连接测试 =====")
        email_conn, email_status = test_network_connection(email_site)
        register_conn, register_status = test_network_connection(register_site)
        
        logging.info(f"临时邮箱网站 ({email_site}): {'可访问' if email_conn else f'不可访问 - {email_status}'}")
        logging.info(f"注册网站 ({register_site}): {'可访问' if register_conn else f'不可访问 - {register_status}'}")
        
        # 初始化ChromeDriver
        try:
            # 方法1: 如果找到ChromeDriver路径，直接使用
            if chrome_driver_path:
                logging.info("使用找到的ChromeDriver路径初始化")
                driver = webdriver.Chrome(
                    service=Service(chrome_driver_path),
                    options=options
                )
            else:
                # 方法2: 尝试使用系统PATH中的ChromeDriver
                logging.info("尝试使用系统PATH中的ChromeDriver")
                driver = webdriver.Chrome(options=options)
            
            # 设置超时
            driver.set_page_load_timeout(60)
            driver.set_script_timeout(60)
            driver.implicitly_wait(10)
            
            logging.info("ChromeDriver初始化成功")
        except Exception as e:
            logging.error(f"ChromeDriver初始化失败: {str(e)}")
            logging.error("\n===== ChromeDriver错误解决指南 =====")
            logging.error("1. 请确保您已安装Google Chrome浏览器")
            logging.error("2. 下载与您Chrome浏览器版本匹配的ChromeDriver:")
            logging.error("   https://chromedriver.chromium.org/downloads")
            logging.error("3. 将chromedriver.exe放在以下任一位置:")
            logging.error("   - 当前目录 (D:/safePro/Register-tools/)")
            logging.error("   - 系统PATH环境变量中的任一目录")
            logging.error("   - 与Chrome浏览器相同的目录")
            logging.error("\n请下载ChromeDriver后重试。")
            raise
        
        # 获取临时邮箱
        email = get_temp_email(driver)
        if not email:
            raise Exception("无法获取临时邮箱")
        
        # 清晰打印获取的邮箱地址
        logging.info(f"===================================")
        logging.info(f"获取到临时邮箱: {email}")
        logging.info(f"===================================")
        
        # 打开新标签页用于注册
        driver.execute_script("window.open('about:blank');")
        driver.switch_to.window(driver.window_handles[1])
        
        # 访问注册页面
        max_attempts = 3
        register_site = 'https://www.daydaymap.com/user/register'
        # 先测试注册网站连接
        connected, status = test_network_connection(register_site)
        if not connected:
            logging.error(f"无法连接到注册网站: {status}")
            raise Exception(f"无法连接到注册网站: {status}")
            
        for attempt in range(max_attempts):
            try:
                driver.get(register_site)
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
        
        # 使用邮箱前缀作为昵称
        email_prefix = email.split('@')[0]
        nickname = email_prefix
        password = generate_password()
        
        logging.info(f"生成的昵称: {nickname}")
        logging.info(f"生成的密码: {password}")
        
        # 填写注册表单
        try:
            # 根据placeholder属性直接定位表单元素
            logging.info("开始定位并填写表单元素...")
            
            # 获取所有输入元素并进行诊断
            all_inputs = driver.find_elements(By.TAG_NAME, 'input')
            for i, element in enumerate(all_inputs):
                try:
                    attrs = {
                        'name': element.get_attribute('name'),
                        'type': element.get_attribute('type'),
                        'placeholder': element.get_attribute('placeholder'),
                        'id': element.get_attribute('id'),
                        'class': element.get_attribute('class')
                    }
                    logging.info(f"诊断：输入元素 {i+1}: {attrs}")
                except Exception as e:
                    logging.warning(f"诊断：获取元素信息失败: {e}")
            
            # 邮箱输入框 - 通过placeholder直接定位
            email_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Please enter phone number or email address']")))
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", email_input)
            time.sleep(0.5)
            email_input.clear()
            email_input.send_keys(email)
            logging.info(f"已填写邮箱: {email}")
            print(f"获取的邮箱地址: {email}")
            
            # 昵称输入框 - 通过placeholder直接定位
            nickname_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Please enter nickname']")))
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", nickname_input)
            time.sleep(0.5)
            nickname_input.clear()
            nickname_input.send_keys(nickname)
            logging.info(f"已填写昵称: {nickname}")
            
            # 密码输入框 - 通过placeholder直接定位
            password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Please enter password']")))
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", password_input)
            time.sleep(0.5)
            password_input.clear()
            password_input.send_keys(password)
            logging.info("已填写密码")
            
            # 确认密码输入框 - 通过placeholder直接定位
            confirm_password_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Please confirm password']")))
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", confirm_password_input)
            time.sleep(0.5)
            confirm_password_input.clear()
            confirm_password_input.send_keys(password)
            logging.info("已确认密码")
            
            # 智能触发验证码发送
            try:
                logging.info("调用智能验证码触发函数...")
                trigger_success = trigger_verification_code(driver)
                if not trigger_success:
                    logging.warning("验证码发送触发未成功，但将继续尝试获取验证码")
            except Exception as e:
                logging.error(f"触发验证码发送时出错: {e}")
                # 即使出错也继续，尝试获取验证码
            
            # 切换回临时邮箱标签页获取验证码
            code = None
            if len(driver.window_handles) > 0:
                driver.switch_to.window(driver.window_handles[0])
                code = get_verification_code(driver)
                
                if code:
                    logging.info(f"获取到验证码: {code}")
                    
                    # 切换回注册标签页填写验证码
                    if len(driver.window_handles) > 1:
                        driver.switch_to.window(driver.window_handles[1])
                        
                        # 填写验证码 - 增强版定位策略
                        code_input = None
                        code_locators = [
                            (By.XPATH, "//input[@placeholder='验证码' or @placeholder='Verification Code' or @placeholder='code']"),
                            (By.NAME, 'code'),
                            (By.ID, 'code'),
                            (By.CSS_SELECTOR, "input[name='code']"),
                            (By.XPATH, "//input[contains(@class, 'code')]"),
                            (By.XPATH, "//input[5]")  # 使用索引定位作为最后手段
                        ]
                        
                        for i, (by, value) in enumerate(code_locators):
                            try:
                                logging.info(f"尝试定位验证码输入框 (方式 {i+1}/{len(code_locators)}): {by}={value}")
                                # 先滚动到元素可见
                                code_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((by, value)))
                                if code_input:
                                    # 尝试滚动元素到可见区域
                                    driver.execute_script("arguments[0].scrollIntoView(true);", code_input)
                                    time.sleep(0.5)
                                    logging.info("成功定位验证码输入框")
                                    break
                            except Exception as e:
                                logging.warning(f"定位验证码输入框失败 (方式 {i+1}): {e}")
                        
                        if code_input:
                            code_input.clear()
                            code_input.send_keys(code)
                            logging.info(f"已填写验证码: {code}")
                        else:
                            logging.error("无法定位验证码输入框")
                        
                        # 勾选同意协议 - 增强版定位策略
                        agreement_checked = False
                        agreement_locators = [
                            # 针对用户提供的HTML结构的特定定位器
                            (By.XPATH, "//span[contains(@class, 'ant-checkbox-label')]"),
                            (By.XPATH, "//span[contains(@class, 'ant-typography') and contains(text(), '我已阅读并同意')]/parent::span"),
                            (By.XPATH, "//span[contains(@class, 'css-zqbva3') and contains(text(), '我已阅读并同意')]/parent::span"),
                            
                            # 原有定位器
                            (By.CSS_SELECTOR, '.agreement-checkbox'),
                            (By.ID, 'agreement'),
                            (By.CSS_SELECTOR, '[type="checkbox"]'),
                            (By.XPATH, "//input[@type='checkbox']"),
                            (By.XPATH, "//label[contains(text(), '同意') or contains(text(), 'agree')]"),
                        ]
                        
                        for i, (by, value) in enumerate(agreement_locators):
                            try:
                                logging.info(f"尝试定位同意协议元素 (方式 {i+1}/{len(agreement_locators)}): {by}={value}")
                                agreement_element = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((by, value)))
                                
                                # 先滚动到元素可见
                                driver.execute_script("arguments[0].scrollIntoView(true);", agreement_element)
                                time.sleep(1)
                                
                                # 尝试点击
                                agreement_element.click()
                                logging.info("已勾选同意协议")
                                agreement_checked = True
                                break
                            except Exception as e:
                                logging.warning(f"定位或勾选同意协议失败 (方式 {i+1}): {e}")
                        
                        if not agreement_checked:
                            logging.warning("无法勾选同意协议")
                        
                        # 点击注册按钮 - 增强版定位策略
                        register_button = None
                        register_locators = [
                            # 针对用户提供的HTML结构的特定定位器
                            (By.XPATH, "//button[contains(@class, 'ant-btn-primary') and contains(@class, 'ant-btn-lg') and contains(@class, 'ant-btn-block')]"),
                            (By.XPATH, "//button[contains(@class, 'css-zqbva3') and contains(@class, 'ant-btn') and contains(text(), '注册')]"),
                            (By.XPATH, "//button[contains(@class, 'ant-btn-two-chinese-chars') and contains(text(), '注册')]"),
                            (By.CSS_SELECTOR, "button.ant-btn.css-zqbva3.ant-btn-primary.ant-btn-block"),
                            
                            # 原有定位器
                            (By.XPATH, "//button[contains(text(), '注册')]"),
                            (By.XPATH, "//button[contains(text(), 'Register')]"),
                            (By.XPATH, "//button[@type='submit']"),
                            (By.ID, 'register'),
                            (By.ID, 'submit'),
                            (By.CSS_SELECTOR, "button[type='submit']")
                        ]
                        
                        for i, (by, value) in enumerate(register_locators):
                            try:
                                logging.info(f"尝试定位注册按钮 (方式 {i+1}/{len(register_locators)}): {by}={value}")
                                register_button = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((by, value)))
                                if register_button:
                                    logging.info("成功定位注册按钮")
                                    # 先滚动到按钮可见
                                    driver.execute_script("arguments[0].scrollIntoView(true);", register_button)
                                    time.sleep(1)
                                    register_button.click()
                                    logging.info("已点击注册按钮")
                                    break
                            except Exception as e:
                                logging.warning(f"定位或点击注册按钮失败 (方式 {i+1}): {e}")
                        
                        if not register_button:
                            logging.error("无法定位注册按钮")
                    else:
                        logging.error("注册标签页不存在")
                else:
                    logging.error("无法获取验证码")
            else:
                logging.error("临时邮箱标签页不存在")
                
            # 如果没有获取到验证码，记录错误信息
            if not code:
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
                # 提前结束，不再继续执行
                return
                
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

# 通用元素等待函数
def wait_for_element(driver, by, value, timeout=10, description="元素"):
    """通用元素等待函数，带详细日志和重试逻辑"""
    logging.info(f"等待{description}: {by}={value}")
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
        # 确保元素可见
        WebDriverWait(driver, timeout).until(
            EC.visibility_of(element)
        )
        # 滚动到元素可见
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        time.sleep(0.5)
        logging.info(f"成功找到{description}")
        return element
    except Exception as e:
        logging.error(f"等待{description}失败: {e}")
        return None

# 安全点击函数
def safe_click(driver, element, description="元素"):
    """安全点击函数，尝试多种点击方式"""
    if not element:
        logging.error(f"无法点击{description}: 元素不存在")
        return False
    
    # 先滚动到元素
    try:
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        time.sleep(0.5)
    except Exception as e:
        logging.warning(f"滚动到{description}时出错: {e}")
    
    # 尝试普通点击
    try:
        element.click()
        logging.info(f"成功点击{description} (普通点击)")
        return True
    except Exception as e1:
        logging.warning(f"普通点击{description}失败: {e1}")
        
    # 尝试JavaScript点击
    try:
        driver.execute_script("arguments[0].click();", element)
        logging.info(f"成功点击{description} (JavaScript点击)")
        return True
    except Exception as e2:
        logging.warning(f"JavaScript点击{description}失败: {e2}")
        
    # 尝试ActionChains点击
    try:
        actions = ActionChains(driver)
        actions.move_to_element(element).click().perform()
        logging.info(f"成功点击{description} (ActionChains点击)")
        return True
    except Exception as e3:
        logging.error(f"ActionChains点击{description}失败: {e3}")
    
    return False

# 智能验证码发送函数
def trigger_verification_code(driver):
    """
    智能触发验证码发送，尝试多种策略确保验证码能够发送
    
    Args:
        driver: WebDriver实例
    
    Returns:
        bool: 是否成功触发验证码发送
    """
    logging.info("开始尝试触发验证码发送...")
    
    # 验证码输入框定位策略
    verification_input_locators = [
        (By.XPATH, "//input[@placeholder='Please enter the verification code']"),
        (By.XPATH, "//input[contains(@placeholder, 'verification')]"),
        (By.XPATH, "//input[contains(@placeholder, '验证码')]"),
        (By.XPATH, "//input[@type='text' and contains(@class, 'verification')]"),
        (By.XPATH, "//input[@id='verification-code']"),
        (By.XPATH, "//input[contains(@id, 'code')]")
    ]
    
    verification_input = None
    
    # 尝试定位验证码输入框
    for locator_type, locator_value in verification_input_locators:
        try:
            verification_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((locator_type, locator_value)))
            logging.info(f"成功定位到验证码输入框: {locator_type}={locator_value}")
            
            # 滚动到验证码输入框可见
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", verification_input)
            time.sleep(0.5)
            break
        except Exception as e:
            logging.warning(f"使用定位器 {locator_type}={locator_value} 未找到验证码输入框: {e}")
    
    if not verification_input:
        logging.error("无法定位验证码输入框")
        return False
    
    # 保存当前窗口句柄，以便后续可能的操作
    current_window = driver.current_window_handle
    
    # 综合触发策略
    strategies = []
    
    # 策略1: 查找父元素内的可点击元素
    try:
        parent_element = verification_input.find_element(By.XPATH, '..')
        nearby_elements = parent_element.find_elements(By.XPATH, './/*')
        logging.info(f"在验证码输入框父元素中找到 {len(nearby_elements)} 个元素")
        
        # 诊断并添加可能的触发元素
        for i, elem in enumerate(nearby_elements[:15]):  # 限制数量避免过多尝试
            try:
                if elem.is_displayed() and elem.is_enabled() and elem != verification_input:
                    elem_text = elem.text.strip()
                    elem_tag = elem.tag_name
                    elem_class = elem.get_attribute('class')
                    elem_id = elem.get_attribute('id')
                    
                    # 判断是否可能是发送按钮
                    if (elem_tag in ['button', 'a', 'input'] or 
                        'code' in (elem_class or '').lower() or 
                        'send' in (elem_class or '').lower() or
                        '获取' in elem_text or 'send' in elem_text.lower() or 'code' in elem_text.lower()):
                        strategies.append((elem, f"父元素内元素 {i+1}: 标签={elem_tag}, 文本='{elem_text}'"))
            except Exception:
                pass
    except Exception as e:
        logging.warning(f"获取父元素信息失败: {e}")
    
    # 策略2: 查找所有包含code/send相关文本或类名的元素
    try:
        code_elements = driver.find_elements(By.XPATH, 
            "//*[(contains(text(), 'code') or contains(text(), 'Code') or contains(text(), '验证码') or "
            "contains(text(), '获取') or contains(text(), 'send') or contains(text(), 'Send') or "
            "contains(@class, 'code') or contains(@id, 'code') or contains(@class, 'send') or "
            "contains(@id, 'send')) and not contains(@placeholder, 'verification')]"
        )
        
        for elem in code_elements[:10]:  # 限制数量
            try:
                if elem.is_displayed() and elem.is_enabled() and elem != verification_input:
                    elem_text = elem.text.strip()
                    elem_tag = elem.tag_name
                    strategies.append((elem, f"全局code元素: 标签={elem_tag}, 文本='{elem_text}'"))
            except Exception:
                pass
    except Exception as e:
        logging.warning(f"查找全局code元素失败: {e}")
    
    # 策略3: 尝试JavaScript查找和点击
    strategies.append((None, "JavaScript查找策略"))
    
    # 策略4: 点击验证码输入框后重新输入邮箱（模拟用户操作）
    strategies.append((None, "重新输入邮箱策略"))
    
    # 执行所有策略
    success = False
    for elem, strategy_name in strategies:
        try:
            logging.info(f"尝试策略: {strategy_name}")
            
            if elem:
                # 对找到的元素执行点击
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", elem)
                time.sleep(0.5)
                
                # 尝试多种点击方式
                try:
                    elem.click()
                    logging.info(f"成功点击元素: {strategy_name}")
                except:
                    try:
                        driver.execute_script("arguments[0].click();", elem)
                        logging.info(f"通过JavaScript成功点击元素: {strategy_name}")
                    except:
                        try:
                            actions = ActionChains(driver)
                            actions.move_to_element(elem).click().perform()
                            logging.info(f"通过ActionChains成功点击元素: {strategy_name}")
                        except:
                            logging.warning(f"所有点击方式都失败: {strategy_name}")
                            continue
                
                time.sleep(1.5)  # 等待可能的反馈
                
                # 检查是否有成功提示
                try:
                    success_messages = driver.find_elements(By.XPATH, 
                        "//*[contains(text(), '已发送') or contains(text(), 'sent') or contains(text(), 'success') or contains(text(), '成功')]"
                    )
                    if success_messages:
                        for msg in success_messages:
                            if msg.is_displayed():
                                logging.info(f"检测到验证码发送成功提示: {msg.text}")
                                success = True
                                break
                except:
                    pass
                
                if success:
                    break
                
            elif strategy_name == "JavaScript查找策略":
                # JavaScript查找和触发策略
                logging.info("执行JavaScript查找验证码发送按钮")
                
                # 执行复杂的JavaScript查找逻辑
                send_button = driver.execute_script("""
                    // 查找可能的发送按钮
                    function findSendButton() {
                        // 查找包含特定文本的元素
                        const texts = ['发送验证码', 'Send Code', '获取验证码', 'Get Code', 'send', '获取'];
                        for (const text of texts) {
                            const elements = document.querySelectorAll('*');
                            for (const element of elements) {
                                if (element.textContent && element.textContent.includes(text) && 
                                    element.nodeName.match(/^(BUTTON|A|INPUT|SPAN|DIV)$/) &&
                                    element.offsetParent !== null) {
                                    return element;
                                }
                            }
                        }
                        
                        // 查找特定类名的元素
                        const classes = ['send-code', 'get-code', 'code-btn', 'verify-btn'];
                        for (const cls of classes) {
                            const element = document.querySelector(`.${cls}`);
                            if (element && element.offsetParent !== null) {
                                return element;
                            }
                        }
                        
                        // 查找验证码输入框旁边的元素
                        const inputs = document.querySelectorAll('input');
                        for (const input of inputs) {
                            if (input.placeholder && (input.placeholder.includes('verification') || 
                                                       input.placeholder.includes('验证码'))) {
                                const sibling = input.nextElementSibling;
                                if (sibling && sibling.nodeName.match(/^(BUTTON|A|INPUT|SPAN|DIV)$/)) {
                                    return sibling;
                                }
                            }
                        }
                        
                        return null;
                    }
                    
                    const button = findSendButton();
                    if (button) {
                        button.scrollIntoView({behavior: 'smooth', block: 'center'});
                        setTimeout(() => button.click(), 500);
                        return true;
                    }
                    return false;
                """)
                
                if send_button:
                    logging.info("JavaScript成功找到并点击发送按钮")
                    time.sleep(2)
                    success = True
                    break
                
            elif strategy_name == "重新输入邮箱策略":
                # 重新输入邮箱策略
                logging.info("执行重新输入邮箱策略")
                
                # 查找邮箱输入框
                try:
                    email_input = WebDriverWait(driver, 5).until(EC.presence_of_element_located(
                        (By.XPATH, "//input[contains(@placeholder, 'email') or contains(@placeholder, 'mail') or contains(@type, 'email')]")
                    ))
                    
                    # 重新输入邮箱
                    current_email = email_input.get_attribute('value')
                    if current_email:
                        email_input.clear()
                        time.sleep(0.5)
                        email_input.send_keys(current_email)
                        logging.info("已重新输入邮箱，可能触发验证码发送")
                        time.sleep(1)
                        
                        # 点击页面其他地方可能触发验证
                        driver.execute_script("document.body.click();")
                        time.sleep(1)
                except Exception as e:
                    logging.warning(f"重新输入邮箱策略失败: {e}")
        
        except Exception as e:
            logging.warning(f"执行策略时出错 {strategy_name}: {e}")
            
        # 检查是否需要处理滑动验证
        try:
            handle_slider_verification(driver)
        except Exception:
            pass
    
    # 如果所有策略都失败，最后尝试直接点击验证码输入框
    if not success:
        try:
            logging.info("尝试最后策略：点击验证码输入框")
            verification_input.click()
            time.sleep(1)
            verification_input.click()  # 再次点击
            time.sleep(1)
            logging.info("已点击验证码输入框")
        except Exception as e:
            logging.warning(f"点击验证码输入框失败: {e}")
    
    logging.info(f"验证码触发流程完成，{'成功' if success else '可能已尝试所有策略'}")
    return success