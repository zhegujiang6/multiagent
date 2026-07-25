package com.multiagent.ticketservice.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.annotation.Version;
import com.multiagent.ticketservice.state.TicketPriority;
import com.multiagent.ticketservice.state.TicketStatus;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;

@Data
@NoArgsConstructor
@TableName("ticket")
public class Ticket {

    @TableId(type = IdType.AUTO)
    private Long id;
    private String requestId;
    private String conversationId;
    private String userId;
    private String category;
    private TicketPriority priority;
    private String summary;
    private TicketStatus status;
    private String assigneeId;
    private OffsetDateTime deadline;
    @Version
    private Long version;
    private OffsetDateTime createdAt;
    private OffsetDateTime updatedAt;
}
