"use client"

import React from "react"
import Link from "next/link"

import { Icons } from "@/components/icons"
import { CommunityNav } from "@/components/nav/community"
import DynamicNavbar from "@/components/nav/dynamic-nav"
import UserNav from "@/components/nav/user-nav"

interface NavbarProps extends React.HTMLAttributes<HTMLDivElement> { }
export default function Navbar(props: NavbarProps) {
  return (
    <div className="w-full space-x-8 border-b" {...props}>
      <div className="flex h-12 w-full items-center space-x-5 px-5">
        <Link href="/workflows">
          <Icons.logo className="size-5" />
        </Link>
        <DynamicNavbar />
        <div className="flex flex-1 items-center justify-end space-x-6">
          <CommunityNav />
          <UserNav />
        </div>
      </div>
    </div>
  )
}
