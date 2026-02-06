"""
视频任务查询和下载模块
多线程并发查询任务状态，完成后自动下载视频
"""

import os
import json
import logging
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

logger = logging.getLogger(__name__)


class VideoTaskQuery:
    """视频任务查询和下载器"""

    def __init__(self,
                 api_key: str,
                 output_dir: str,
                 detail_url: str = "https://api.wuyinkeji.com/api/sora2/detail",
                 max_workers: int = 5,
                 poll_interval: int = 10,
                 max_poll_time: int = 3600):
        """
        初始化查询器

        Args:
            api_key: 五一科技API密钥
            output_dir: 视频输出目录
            detail_url: 查询接口地址
            max_workers: 最大并发线程数
            poll_interval: 查询间隔（秒）
            max_poll_time: 最大查询时间（秒）
        """
        self.api_key = api_key
        self.detail_url = detail_url
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.poll_interval = poll_interval
        self.max_poll_time = max_poll_time

        # 确保输出目录存在
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        # 线程锁
        self._lock = threading.Lock()
        # 已完成的任务
        self._completed_tasks: set = set()
        # 任务状态缓存
        self._task_status: Dict[str, str] = {}

    def load_tasks_from_report(self, report_path: str) -> List[Dict]:
        """
        从生成报告加载所有任务

        Args:
            report_path: 报告JSON文件路径

        Returns:
            任务列表，每个任务包含 task_id, scene_name 等信息
        """
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report = json.load(f)

            tasks = []
            total_scenes = 0
            null_task_ids = 0

            # 从 N 类事件中提取任务
            for event in report.get("n_events", []):
                total_scenes += 1
                task_id = event.get("task_id")
                if task_id:
                    tasks.append({
                        "task_id": task_id,
                        "scene_name": event.get("scene_name", "unknown"),
                        "event_type": "N"
                    })
                else:
                    null_task_ids += 1

            # 从 R/SR 类事件中提取任务
            for event_type_key in ["r_events", "sr_events"]:
                for event in report.get(event_type_key, []):
                    for scene in event.get("scenes", []):
                        total_scenes += 1
                        task_id = scene.get("task_id")
                        if task_id:
                            tasks.append({
                                "task_id": task_id,
                                "scene_name": scene.get("scene_name", "unknown"),
                                "event_type": event.get("event_type", event_type_key[0].upper())
                            })
                        else:
                            null_task_ids += 1

            logger.info(f"从报告加载统计:")
            logger.info(f"  总场景数: {total_scenes}")
            logger.info(f"  有task_id: {len(tasks)}")
            logger.info(f"  无task_id: {null_task_ids}")

            if null_task_ids > 0:
                logger.warning(f"发现 {null_task_ids} 个场景没有 task_id（可能视频生成未提交或仅提交模式）")

            return tasks

        except Exception as e:
            logger.error(f"加载报告失败: {e}")
            return []

    def query_task_status(self, task_id: str) -> Optional[Dict]:
        """
        查询单个任务状态

        Args:
            task_id: 任务ID

        Returns:
            状态信息字典: {status, url}
        """
        query_url = f"{self.detail_url}?key={self.api_key}&id={task_id}"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset:utf-8;",
            "Authorization": self.api_key
        }

        try:
            response = requests.get(query_url, headers=headers, timeout=30)

            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 200:
                    data = result.get("data", {})
                    if isinstance(data, dict):
                        status = data.get("status")  # 0:排队中 1:成功 2:失败 3:生成中
                        remote_url = data.get("remote_url")

                        # 状态映射
                        status_map = {
                            0: "submitted",
                            1: "success",
                            2: "failed",
                            3: "processing"
                        }

                        return {
                            "status": status_map.get(status, "unknown"),
                            "url": remote_url
                        }

            logger.debug(f"任务 {task_id[:20]}... 查询状态码: {response.status_code}")
            return None

        except Exception as e:
            logger.debug(f"查询任务 {task_id[:20]}... 失败: {e}")
            return None

    def download_video(self, url: str, output_path: str) -> bool:
        """
        下载视频到本地

        Args:
            url: 视频URL
            output_path: 输出文件路径

        Returns:
            是否下载成功
        """
        try:
            response = requests.get(url, timeout=60, stream=True)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"视频下载完成: {output_path}")
                return True
            else:
                logger.warning(f"下载失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"下载视频失败 {output_path}: {e}")
            return False

    def process_single_task(self, task: Dict, start_time: float) -> Dict:
        """
        处理单个任务：轮询直到完成或超时

        Args:
            task: 任务信息字典
            start_time: 开始时间戳

        Returns:
            处理结果字典
        """
        task_id = task["task_id"]
        scene_name = task.get("scene_name", "unknown")

        # 检查是否已处理
        with self._lock:
            if task_id in self._completed_tasks:
                return {"task_id": task_id, "status": "already_completed"}

        logger.info(f"开始处理任务: {scene_name} ({task_id[:20]}...)")

        poll_count = 0
        while time.time() - start_time < self.max_poll_time:
            # 检查是否被其他线程完成
            with self._lock:
                if task_id in self._completed_tasks:
                    return {"task_id": task_id, "status": "completed_by_other"}

            # 查询状态
            status_info = self.query_task_status(task_id)
            poll_count += 1

            if status_info is None:
                logger.warning(f"[{poll_count}] {scene_name}: 查询失败，重试...")
                time.sleep(self.poll_interval)
                continue

            status = status_info.get("status")
            video_url = status_info.get("url")

            # 更新状态缓存
            with self._lock:
                self._task_status[task_id] = status

            if status == "success" and video_url:
                # 下载视频
                video_filename = f"{scene_name}.mp4"
                video_path = os.path.join(self.output_dir, video_filename)

                if self.download_video(video_url, video_path):
                    with self._lock:
                        self._completed_tasks.add(task_id)
                    return {
                        "task_id": task_id,
                        "status": "success",
                        "video_path": video_path,
                        "scene_name": scene_name
                    }
                else:
                    return {
                        "task_id": task_id,
                        "status": "download_failed",
                        "scene_name": scene_name
                    }

            elif status == "failed":
                logger.warning(f"{scene_name}: 任务失败")
                with self._lock:
                    self._completed_tasks.add(task_id)
                return {
                    "task_id": task_id,
                    "status": "failed",
                    "scene_name": scene_name
                }

            elif status in ["submitted", "processing"]:
                logger.info(f"[{poll_count}] {scene_name}: {status}")
                time.sleep(self.poll_interval)

            else:
                logger.warning(f"[{poll_count}] {scene_name}: 未知状态 {status}")
                time.sleep(self.poll_interval)

        # 超时
        logger.warning(f"{scene_name}: 查询超时")
        return {
            "task_id": task_id,
            "status": "timeout",
            "scene_name": scene_name
        }

    def process_all_tasks(self, tasks: List[Dict]) -> Dict:
        """
        并发处理所有任务

        Args:
            tasks: 任务列表

        Returns:
            处理结果汇总
        """
        start_time = time.time()

        if not tasks:
            logger.warning("没有需要处理的任务")
            elapsed_time = time.time() - start_time
            return {
                "total": 0,
                "success": 0,
                "failed": 0,
                "timeout": 0,
                "elapsed_time": elapsed_time,
                "results": []
            }

        logger.info(f"开始并发处理 {len(tasks)} 个任务，最大线程数: {self.max_workers}")

        results = []
        success_count = 0
        failed_count = 0
        timeout_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="VideoQuery") as executor:
            # 提交所有任务
            future_to_task = {}
            for task in tasks:
                future = executor.submit(self.process_single_task, task, start_time)
                future_to_task[future] = task

            # 收集结果
            for i, future in enumerate(as_completed(future_to_task), 1):
                task = future_to_task[future]
                scene_name = task.get("scene_name", "unknown")

                try:
                    result = future.result()
                    results.append(result)

                    status = result.get("status")
                    if status == "success":
                        success_count += 1
                        logger.info(f"[{i}/{len(tasks)}] ✓ {scene_name}: 完成")
                    elif status == "failed":
                        failed_count += 1
                        logger.info(f"[{i}/{len(tasks)}] ✗ {scene_name}: 失败")
                    elif status == "timeout":
                        timeout_count += 1
                        logger.info(f"[{i}/{len(tasks)}] ⏱ {scene_name}: 超时")

                except Exception as e:
                    logger.error(f"处理任务失败 {scene_name}: {e}")
                    results.append({
                        "task_id": task.get("task_id"),
                        "status": "error",
                        "error": str(e)
                    })

        # 汇总结果
        elapsed_time = time.time() - start_time
        summary = {
            "total": len(tasks),
            "success": success_count,
            "failed": failed_count,
            "timeout": timeout_count,
            "elapsed_time": elapsed_time,
            "results": results
        }

        logger.info(f"处理完成! 总计: {len(tasks)}, 成功: {success_count}, 失败: {failed_count}, 超时: {timeout_count}, 耗时: {elapsed_time:.1f}秒")

        # 保存结果报告
        self._save_result_report(summary)

        return summary

    def _save_result_report(self, summary: Dict):
        """保存结果报告"""
        report_path = os.path.join(self.output_dir, "download_report.json")
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            logger.info(f"结果报告已保存: {report_path}")
        except Exception as e:
            logger.error(f"保存结果报告失败: {e}")


def query_and_download_videos(report_path: str,
                             api_key: str,
                             output_dir: Optional[str] = None,
                             max_workers: int = 5) -> Dict:
    """
    便捷函数：从报告查询并下载视频

    Args:
        report_path: 生成报告JSON文件路径
        api_key: 五一科技API密钥
        output_dir: 视频输出目录（默认与报告同目录）
        max_workers: 最大并发线程数

    Returns:
        处理结果汇总
    """
    # 如果没有指定输出目录，使用报告所在目录
    if output_dir is None:
        output_dir = str(Path(report_path).parent)

    # 创建查询器
    query = VideoTaskQuery(
        api_key=api_key,
        output_dir=output_dir,
        max_workers=max_workers
    )

    # 加载任务
    tasks = query.load_tasks_from_report(report_path)

    # 处理所有任务
    return query.process_all_tasks(tasks)
