package com.multiagent.ticketservice.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.multiagent.ticketservice.state.TicketStatus;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;

@Data
@NoArgsConstructor
@TableName("ticket_status_log")
public class TicketStatusLog {

    @TableId(type = IdType.AUTO)
    private Long id;
    private Long ticketId;
    private TicketStatus fromStatus;
    private TicketStatus toStatus;
    private String operatorId;
    private String reason;
    private OffsetDateTime createdAt;
}
