package com.multiagent.ticketservice.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.multiagent.ticketservice.entity.TicketStatusLog;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface TicketStatusLogMapper extends BaseMapper<TicketStatusLog> {
}
