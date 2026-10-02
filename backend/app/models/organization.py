"""组织架构模型 - 部门、岗位、职级、人员岗位关联"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Department(Base):
    """部门表 - 多级树形结构"""

    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"), nullable=True, index=True, comment="所属单位ID")
    parent_id = Column(Integer, ForeignKey("departments.id"), nullable=True, comment="父部门ID")
    name = Column(String(100), nullable=False, comment="部门名称")
    code = Column(String(50), nullable=True, comment="部门编码")
    manager_id = Column(Integer, ForeignKey("persons.id"), nullable=True, comment="部门负责人ID")
    level = Column(Integer, default=1, nullable=False, comment="层级深度")
    sort = Column(Integer, default=0, nullable=False, comment="排序")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    description = Column(Text, nullable=True, comment="部门描述")
    is_deleted = Column(Boolean, default=False, nullable=False, comment="是否已删除")
    deleted_at = Column(DateTime, nullable=True, comment="删除时间")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # 关系
    unit = relationship("Unit", backref="departments")
    parent = relationship("Department", remote_side=[id], backref="children")
    manager = relationship("Person", foreign_keys=[manager_id])
    person_positions = relationship("PersonPosition", back_populates="department")

    def __repr__(self):
        return f"<Department {self.name}>"


class Rank(Base):
    """职级表 - 职级体系"""

    __tablename__ = "ranks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, comment="职级名称")
    code = Column(String(50), unique=True, nullable=False, comment="职级编码")
    category = Column(String(50), nullable=True, comment="职级类别: 管理岗/技术岗/工勤岗")
    level = Column(Integer, default=1, nullable=False, comment="职级等级(1-15)")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    description = Column(Text, nullable=True, comment="职级描述")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    person_positions = relationship("PersonPosition", back_populates="rank")

    def __repr__(self):
        return f"<Rank {self.name}>"


class Position(Base):
    """岗位表 - 岗位字典"""

    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="岗位名称")
    code = Column(String(50), unique=True, nullable=False, comment="岗位编码")
    category = Column(String(50), nullable=True, comment="岗位类别: 管理岗/专业技术岗/工勤技能岗")
    allowed_ranks = Column(JSON, nullable=True, comment="可任职级ID列表")
    is_leadership = Column(Boolean, default=False, nullable=False, comment="是否领导岗位")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    description = Column(Text, nullable=True, comment="岗位职责描述")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    person_positions = relationship("PersonPosition", back_populates="position")

    def __repr__(self):
        return f"<Position {self.name}>"


class PersonPosition(Base):
    """人员岗位关联表 - 支持多岗位和历史记录"""

    __tablename__ = "person_positions"

    id = Column(Integer, primary_key=True, index=True)
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False, index=True, comment="人员ID")
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True, index=True, comment="部门ID")
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=True, index=True, comment="岗位ID")
    rank_id = Column(Integer, ForeignKey("ranks.id"), nullable=True, index=True, comment="职级ID")
    is_primary = Column(Boolean, default=True, nullable=False, comment="是否主岗位")
    start_date = Column(Date, nullable=False, comment="任职开始日期")
    end_date = Column(Date, nullable=True, comment="任职结束日期，null表示当前在职")
    is_current = Column(Boolean, default=True, nullable=False, comment="是否当前任职")
    appointment_no = Column(String(50), nullable=True, comment="任命文号")
    remark = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    person = relationship("Person", backref="person_positions")
    department = relationship("Department", back_populates="person_positions")
    position = relationship("Position", back_populates="person_positions")
    rank = relationship("Rank", back_populates="person_positions")

    def __repr__(self):
        return f"<PersonPosition person={self.person_id} pos={self.position_id}>"