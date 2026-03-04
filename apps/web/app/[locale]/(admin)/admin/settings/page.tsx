"use client"

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { authClient } from "@/lib/auth-client"
import SystemLogsPage from "./logs/page"

export default function SettingsPage() {
    const { data: session } = authClient.useSession()
    const user = session?.user

    const name = user?.name || user?.email || ""
    const initials = name
        .split(' ')
        .map(n => n[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()

    return (
        <div className="space-y-6 max-w-5xl">
            <div className="flex flex-col gap-2">
                <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
                <p className="text-muted-foreground">
                    Manage system configurations, your profile, and view audit logs.
                </p>
            </div>

            <Tabs defaultValue="profile" className="space-y-4">
                <TabsList>
                    <TabsTrigger value="profile">Profile</TabsTrigger>
                    <TabsTrigger value="general">General</TabsTrigger>
                    <TabsTrigger value="logs">System Logs</TabsTrigger>
                </TabsList>
                
                <TabsContent value="profile" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>Your Profile</CardTitle>
                            <CardDescription>Manage your personal administrator account details.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="flex items-center gap-6">
                                <Avatar className="h-20 w-20">
                                    <AvatarImage src={user?.image || ""} alt={name} />
                                    <AvatarFallback className="bg-primary/10 text-primary text-2xl font-semibold">
                                        {initials}
                                    </AvatarFallback>
                                </Avatar>
                                <div>
                                    <h3 className="text-lg font-medium">Profile Picture</h3>
                                    <p className="text-sm text-muted-foreground">Manage your avatar through Better Auth.</p>
                                </div>
                            </div>
                            <Separator />
                            <div className="grid gap-6 md:grid-cols-2">
                                <div className="space-y-2">
                                    <Label htmlFor="name">Full Name</Label>
                                    <Input id="name" defaultValue={user?.name || ""} placeholder="E.g. John Doe" />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="email">Email Address</Label>
                                    <Input id="email" defaultValue={user?.email || ""} readOnly disabled className="bg-muted text-muted-foreground" />
                                    <p className="text-xs text-muted-foreground">Email addresses cannot be changed.</p>
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="role">Admin Role</Label>
                                    <Input id="role" defaultValue={(user as any)?.role || "Editor"} readOnly disabled className="bg-muted text-muted-foreground capitalize" />
                                </div>
                            </div>
                        </CardContent>
                        <CardFooter className="border-t px-6 py-4">
                            <Button>Save Changes</Button>
                        </CardFooter>
                    </Card>
                </TabsContent>

                <TabsContent value="general" className="space-y-4">
                    <Card>
                        <CardHeader>
                            <CardTitle>System Preferences</CardTitle>
                            <CardDescription>Configure global application settings and platform overrides.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="space-y-2">
                                <Label htmlFor="site-name">Platform Name</Label>
                                <Input id="site-name" defaultValue="Awaqi Support AI" />
                                <p className="text-xs text-muted-foreground">This name is displayed in emails and meta tags.</p>
                            </div>
                            
                            <Separator />

                            <div className="space-y-4">
                                <h3 className="text-lg font-medium">Access Controls</h3>
                                <div className="flex items-center justify-between rounded-lg border p-4">
                                    <div className="space-y-0.5">
                                        <Label className="text-base cursor-pointer" htmlFor="customer-signup">Allow Customer Signups</Label>
                                        <p className="text-sm text-muted-foreground">
                                            Enable guests to register new customer accounts from the home page.
                                        </p>
                                    </div>
                                    <Switch id="customer-signup" defaultChecked />
                                </div>
                                <div className="flex items-center justify-between rounded-lg border p-4">
                                    <div className="space-y-0.5">
                                        <Label className="text-base text-destructive cursor-pointer" htmlFor="maintenance-mode">Maintenance Mode</Label>
                                        <p className="text-sm text-muted-foreground">
                                            Disable customer access and show a down-for-maintenance page.
                                        </p>
                                    </div>
                                    <Switch id="maintenance-mode" />
                                </div>
                            </div>
                        </CardContent>
                        <CardFooter className="border-t px-6 py-4 flex justify-between">
                            <Button variant="outline">Reset Defaults</Button>
                            <Button>Apply Settings</Button>
                        </CardFooter>
                    </Card>
                </TabsContent>

                <TabsContent value="logs" className="space-y-4">
                    <SystemLogsPage />
                </TabsContent>
            </Tabs>
        </div>
    )
}
