import React from "react"
import { useWorkflowBuilder } from "@/providers/builder"
import { useWorkflow } from "@/providers/workflow"
import {
  BellDotIcon,
  CalendarCheck,
  ChevronDownIcon,
  CircleCheckBigIcon,
  EyeIcon,
  LayoutListIcon,
  ScanSearchIcon,
  WebhookIcon,
} from "lucide-react"
import { Node, NodeProps, Position, useNodeId } from "reactflow"

import { Schedule, Webhook } from "@/types/schemas"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Separator } from "@/components/ui/separator"
import {
  Table,
  TableBody,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { getIcon } from "@/components/icons"
import NoContent from "@/components/no-content"
import { CustomHandle } from "@/components/workspace/canvas/custom-handle"

export interface TriggerNodeData {
  type: "trigger"
  title: string
  status: "online" | "offline"
  isConfigured: boolean
  entrypointId?: string
  webhook: Webhook
  schedules: Schedule[]
}
export type TriggerNodeType = Node<TriggerNodeData>
export const TriggerTypename = "trigger" as const

export default React.memo(function TriggerNode({
  data: { title, isConfigured, type },
  selected,
}: NodeProps<TriggerNodeData>) {
  const id = useNodeId()
  const { workflowId, getNode, reactFlow } = useWorkflowBuilder()
  const { workflow } = useWorkflow()

  if (!workflow) {
    return null
  }

  return (
    <Card className={cn("min-w-72", selected && "shadow-xl drop-shadow-xl")}>
      <CardHeader className="p-4">
        <div className="flex w-full items-center space-x-4">
          {getIcon(type, {
            className: "size-10 p-2",
          })}

          <div className="flex w-full flex-1 justify-between space-x-12">
            <div className="flex flex-col">
              <CardTitle className="flex w-full items-center justify-between text-xs font-medium leading-none">
                <div className="flex w-full">{title}</div>
              </CardTitle>
              <CardDescription className="mt-2 text-xs text-muted-foreground">
                Workflow triggers
              </CardDescription>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" className="m-0 size-6 p-0">
                  <ChevronDownIcon className="m-1 size-4 text-muted-foreground" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem disabled>
                  <ScanSearchIcon className="mr-2 size-4" />
                  <span className="text-xs">Search events</span>
                </DropdownMenuItem>
                <DropdownMenuItem disabled>
                  <EyeIcon className="mr-2 size-4" />
                  <span className="text-xs">View logs</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardHeader>
      <Separator />
      <div className="p-4">
        <div className="space-y-4">
          <div
            className={cn(
              "flex h-8 items-center justify-center gap-1 rounded-lg border text-xs text-muted-foreground",
              workflow?.webhook.status === "offline"
                ? "bg-muted-foreground/5 text-muted-foreground/50"
                : "bg-background text-emerald-500"
            )}
          >
            <WebhookIcon className="size-3" />
            <span>Webhook</span>
            <span
              className={cn(
                "ml-2 inline-block size-2 rounded-full ",
                workflow.webhook.status === "online"
                  ? "bg-emerald-500"
                  : "bg-gray-300"
              )}
            />
          </div>

          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="h-8 text-center text-xs">
                    <div className="flex items-center justify-center gap-1">
                      <CalendarCheck className="size-3" />
                      <span>Schedules</span>
                    </div>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {workflow.schedules.map(({ id, cron }) => (
                  <TableRow key={id}>
                    <TableCell>{cron}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
              <TableFooter>
                <NoContent
                  className="min-h-8 text-xs text-muted-foreground/70"
                  message="No schedules"
                />
              </TableFooter>
            </Table>
          </div>
        </div>
      </div>
      <Separator />
      <CardContent className="p-4 py-3">
        <div className="grid grid-cols-2 space-x-4 text-xs text-muted-foreground">
          <div className="flex items-center space-x-2">
            {isConfigured ? (
              <CircleCheckBigIcon className="size-4 text-emerald-500" />
            ) : (
              <LayoutListIcon className="size-4 text-gray-400" />
            )}
            <span className="text-xs capitalize">{"Not configured"}</span>
          </div>
          <div className="flex items-center justify-end">
            <BellDotIcon className="mr-2 size-3" />0
          </div>
        </div>
      </CardContent>

      <CustomHandle
        type="source"
        position={Position.Bottom}
        className="w-16 !bg-gray-500"
        style={{ width: 8, height: 8 }}
        isConnectable={1}
      />
    </Card>
  )
})
