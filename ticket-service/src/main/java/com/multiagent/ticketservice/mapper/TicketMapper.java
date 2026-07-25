package com.multiagent.ticketservice.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.multiagent.ticketservice.entity.Ticket;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;

@Mapper
public interface TicketMapper extends BaseMapper<Ticket> {

    @Select("SELECT * FROM ticket WHERE request_id = #{requestId}")
    Ticket selectByRequestId(String requestId);
}
